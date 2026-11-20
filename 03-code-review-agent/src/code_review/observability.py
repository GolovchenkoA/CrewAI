"""Optional OpenTelemetry tracing: one span per review, exported over OTLP/HTTP.

Enabled only when OTEL_EXPORTER_OTLP_ENDPOINT is set (for example http://localhost:4318 or a Langfuse
OTLP endpoint); otherwise `span()` does nothing. The OpenTelemetry packages are imported lazily.

Tracing must never break a review: setup errors turn tracing off with one warning, and export errors
(backend not running) happen on a background thread with a short timeout and are logged as warnings.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

EXPORT_TIMEOUT_SECONDS = (
    2  # a dead backend must not stall the exporter or the shutdown flush
)

_tracer = None
_initialised = False


class _WarnOnly(logging.Filter):
    """The exporter logs a failed export as an ERROR; for an optional backend a WARNING is enough."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno > logging.WARNING:
            record.levelno, record.levelname = logging.WARNING, "WARNING"
        return True


def _get_tracer():
    global _tracer, _initialised
    if _initialised:
        return _tracer
    _initialised = True
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        for name in (
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
            "opentelemetry.sdk.trace.export",
        ):
            logging.getLogger(name).addFilter(_WarnOnly())

        provider = TracerProvider(
            resource=Resource.create({"service.name": "code-review-agent"})
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    timeout=EXPORT_TIMEOUT_SECONDS
                ),  # endpoint from the env
                schedule_delay_millis=2000,
                export_timeout_millis=EXPORT_TIMEOUT_SECONDS * 1000,
            )
        )
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("code_review")
    except Exception as exc:  # noqa: BLE001 - any setup problem: run without tracing
        logger.warning("Tracing disabled, could not set up OpenTelemetry: %s", exc)
        _tracer = None
    if _tracer is not None:
        _instrument_crewai(provider)
        _instrument_anthropic(provider)
    return _tracer


def _instrument_crewai(provider) -> None:
    """Add crew, task and tool spans (OpenInference) below the `review` span; optional, never fatal."""
    try:
        from openinference.instrumentation.crewai import CrewAIInstrumentor

        CrewAIInstrumentor().instrument(tracer_provider=provider)
    except Exception as exc:  # noqa: BLE001 - the review span still works without it
        logger.warning("CrewAI spans disabled, could not instrument CrewAI: %s", exc)


def _instrument_anthropic(provider) -> None:
    """Add one span per Claude API call (model, messages, token counts); optional, never fatal.

    crewai's Claude provider uses the official `anthropic` SDK, which this patches. Local (Ollama)
    models are not covered.
    """
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        AnthropicInstrumentor().instrument(tracer_provider=provider)
    except Exception as exc:  # noqa: BLE001 - the other spans still work without it
        logger.warning("LLM spans disabled, could not instrument Anthropic: %s", exc)


@contextmanager
def span(name: str, **attributes) -> Iterator[dict]:
    """`with span("review", title=...) as attrs:` - add result attributes to `attrs` before leaving."""
    tracer = _get_tracer()
    extra: dict = {}
    if tracer is None:
        yield extra
        return
    with tracer.start_as_current_span(name, attributes=attributes) as s:
        yield extra
        for key, value in extra.items():
            s.set_attribute(key, value)
