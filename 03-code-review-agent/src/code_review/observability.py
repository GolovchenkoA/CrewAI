"""Optional OpenTelemetry tracing: one span per review, exported over OTLP/HTTP.

Enabled only when OTEL_EXPORTER_OTLP_ENDPOINT is set (for example http://localhost:4318 or a Langfuse
OTLP endpoint); otherwise `span()` does nothing. The OpenTelemetry packages are imported lazily.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager

_tracer = None
_initialised = False


def _get_tracer():
    global _tracer, _initialised
    if _initialised:
        return _tracer
    _initialised = True
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({"service.name": "code-review-agent"})
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )  # reads the endpoint from the env
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("code_review")
    return _tracer


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
