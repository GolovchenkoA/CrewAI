# Build from the REPOSITORY ROOT:  docker build -f 03-code-review-agent/Dockerfile -t code-review-agent .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# the workspace needs every member's manifest to resolve; only this member is installed
COPY pyproject.toml uv.lock .python-version ./
COPY 01-research-report-crew/pyproject.toml 01-research-report-crew/pyproject.toml
COPY 02-support-ticket-triage-flow/pyproject.toml 02-support-ticket-triage-flow/pyproject.toml
COPY 03-code-review-agent/pyproject.toml 03-code-review-agent/pyproject.toml

# dependencies first (cached layer), then the project code
RUN uv sync --frozen --no-dev --no-install-workspace --package code-review-agent
COPY 03-code-review-agent/src 03-code-review-agent/src
COPY 03-code-review-agent/samples 03-code-review-agent/samples
RUN uv sync --frozen --no-dev --package code-review-agent

WORKDIR /app/03-code-review-agent
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8080/health')"
CMD ["uvicorn", "code_review.api:app", "--host", "0.0.0.0", "--port", "8080"]
