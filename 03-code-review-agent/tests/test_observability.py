import logging
import time

from code_review import observability


def reset(monkeypatch):
    monkeypatch.setattr(observability, "_tracer", None)
    monkeypatch.setattr(observability, "_initialised", False)


def test_span_is_a_noop_without_an_endpoint(monkeypatch):
    reset(monkeypatch)

    with observability.span("review", title="x") as attrs:
        attrs["findings"] = 1

    assert observability._tracer is None


def test_unreachable_backend_does_not_break_the_review(monkeypatch):
    reset(monkeypatch)
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9"
    )  # nothing listens here

    with observability.span("review", title="x") as attrs:
        attrs["findings"] = 2
        result = "review done"
    started = time.monotonic()
    from opentelemetry import trace

    trace.get_tracer_provider().shutdown()  # flushes the span to the dead backend

    assert result == "review done"
    assert time.monotonic() - started < 15  # a dead backend must not stall the flush


def test_setup_failure_turns_tracing_off_with_a_warning(monkeypatch, caplog):
    reset(monkeypatch)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9")

    def broken(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("opentelemetry.sdk.trace.TracerProvider", broken)

    with (
        caplog.at_level(logging.WARNING, logger=observability.logger.name),
        observability.span("review") as attrs,
    ):
        attrs["ok"] = True

    assert observability._tracer is None
    assert "Tracing disabled" in caplog.text
