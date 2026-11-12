# 03 - Production-Grade Code Review Agent

## 1. What the project does

A crew that reviews pull requests and posts a summary comment. A FastAPI service receives GitHub `pull_request` webhooks (or you can feed it a local `.diff` file), then three agents review in parallel:

- **Security reviewer**: injection, secrets, unsafe deserialization.
- **Style reviewer**: naming, structure, dead code.
- **Test-coverage reviewer**: changed code without tests.

A lead reviewer merges the findings into one prioritised comment. The service runs in Docker and can be called from a Spring Boot app over REST.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| Planning mode (`planning=True`) | crew config |
| `crewai train` and `crewai test` (evaluation of runs) | commands below |
| Event listeners and callbacks (`BaseEventListener`) | `listeners.py` |
| Observability (OpenTelemetry / Langfuse, optional) | `observability.py` |
| Token and cost tracking (`usage_metrics`) | logged per review |
| Retries, rate limits (`max_rpm`, `max_retry_limit`, timeouts) | agent config |
| Batch processing (`kickoff_for_each`, `kickoff_async`) | multi-PR runs |
| Structured output (`output_pydantic`) | findings schema |
| Task guardrails | reject comments without file/line refs |
| Custom tools (git diff parser, repo file reader) | `tools/` |
| Containerised deployment | `Dockerfile`, `docker-compose.yml` |
| LiteLLM, Claude / local switch | `llm_factory.py` |

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root: one shared `.venv` and one `uv.lock` for all three projects. For first-time setup on a new computer (installing uv, Ollama, cloning) see the [root README](../README.md#setting-up-on-another-computer).

Requirements: [uv](https://docs.astral.sh/uv/) (it downloads Python 3.12 automatically, pinned by the root `.python-version`; CrewAI 1.15.x does not support Python 3.14), Docker (optional), an Anthropic API key **or** Ollama. Posting comments needs a GitHub token (`GITHUB_TOKEN`, scope `pull_requests:write`); without it the review is only printed.

### Install dependencies

Run `uv sync` once from the **repository root**, then create this project's `.env`.

**Windows (PowerShell)**
```powershell
cd <repo-root>
uv sync                                  # or: uv sync --package code-review-agent
cd 03-code-review-agent
Copy-Item .env.example .env
```

**Linux / macOS**
```bash
cd <repo-root>
uv sync                                  # or: uv sync --package code-review-agent
cd 03-code-review-agent
cp .env.example .env
```

No manual activation is needed; prefix commands with `uv run`. To activate the shared environment anyway: `..\.venv\Scripts\Activate.ps1` (Windows) or `source ../.venv/bin/activate` (Linux).

### Choose the LLM (edit `.env`)

- Claude: `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY=...`
- Local: `LLM_PROVIDER=local`, then `ollama pull qwen3.5:9b` (~6.6 GB, fits 8 GB VRAM) and start Ollama with a larger context:
  - Windows: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
  - Linux: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

Large diffs overflow small local context windows; the service chunks diffs per file (`MAX_DIFF_TOKENS`).

### Run

From `03-code-review-agent/`. Review a local diff (no GitHub needed):
```bash
uv run python -m code_review.main --diff samples/example.diff
```

Run the webhook service:
```bash
uv run uvicorn code_review.api:app --host 0.0.0.0 --port 8080
curl -X POST http://localhost:8080/review -H "Content-Type: application/json" -d @samples/pr_event.json
```

Train and evaluate:
```bash
uv run crewai train -n 3 -f training.pkl
uv run crewai test -n 2 -m anthropic/claude-sonnet-5-5
```

### Docker

The image installs from the workspace lock file, so the Docker build context is the **repository root**:

```bash
docker compose up --build        # service on http://localhost:8080
```
For a local LLM from the container, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` (Windows/macOS) or run Ollama on the Docker network (Linux).

### Optional observability

Set `OTEL_EXPORTER_OTLP_ENDPOINT` (or Langfuse keys) in `.env`; traces and token usage then appear in your backend.
