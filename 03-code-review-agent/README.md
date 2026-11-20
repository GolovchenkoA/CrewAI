# 03 - Production-Grade Code Review Agent

## 1. What the project does

A crew that reviews pull requests and posts a summary comment. A FastAPI service receives GitHub `pull_request` webhooks (or you can feed it a local `.diff` file), then three agents review in parallel:

- **Security reviewer**: injection, secrets, unsafe deserialization.
- **Style reviewer**: naming, structure, dead code.
- **Test-coverage reviewer**: changed code without tests.

A lead reviewer merges the findings into one prioritised comment. The service runs in Docker and can be called from a Spring Boot app over REST.

## 2. How it works

```
diff ──► chunks (MAX_DIFF_TOKENS, lines numbered) ──► reviewers_crew, once per chunk (kickoff_for_each)
           security ┐ run in parallel (async tasks)
           style    ┘
           test coverage (sync task, has the changed-files tool)
     ──► merge: drop duplicates and findings about files not in the diff, sort by severity
     ──► lead_crew: one agent writes the Markdown comment (guardrail: every finding as `path:line`)
         no findings -> no LLM call; guardrail gives up -> plain comment built from the findings
```

| Aspect | Where |
|---|---|
| Planning mode (`planning=True`) | `crew.py`, switch `PLANNING` (default off: one more LLM call per chunk) |
| `crew.train` and `crew.test` (model-graded evaluation) | `main.py`, scripts `code_review_train`, `code_review_test` |
| Event listeners (`BaseEventListener`) | `listeners.py` (task, tool and failure events) |
| Observability (OpenTelemetry / Langfuse, optional) | `observability.py`, one span per review |
| Token tracking per crew and agent | `usage_tracker.py`, printed after a run, logged per review by the service |
| Retries, rate limits, timeouts | agent `max_rpm`, `max_retry_limit`, `max_execution_time` in `crew.py` |
| Batch processing | `kickoff_for_each` over diff chunks; `--diff` is repeatable for several PRs |
| Async tasks | security and style reviewers run concurrently |
| Structured output (`output_pydantic`) | `models.py` (`ReviewFindings`) |
| Task guardrail | `crew.py`: comment must contain `file:line` for each finding; retries, then falls back |
| Custom tools | `tools/diff_parser.py` (parser/chunker), `tools/repo_tools.py` (`read_repo_file`, `list_changed_files`) |
| FastAPI webhook | `api.py` (HMAC signature check, background review, `/review/diff` for REST clients) |
| Containerised deployment | `Dockerfile`, `docker-compose.yml` |
| Claude / local LLM switch (native providers) | `llm_factory.py` |

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
- Local: `LLM_PROVIDER=local`, then `ollama pull qwen3.5:9b` or `ollama pull qwen3:4b` (~6.6 GB, fits 8 GB VRAM) and start Ollama with a larger context:
  - Windows: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
  - Linux: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

Large diffs overflow small local context windows; the service chunks diffs per file (`MAX_DIFF_TOKENS`).

### Run

From `03-code-review-agent/`. Review a local diff (no GitHub needed; `--diff` can be repeated):
```bash
uv run code_review_run --diff samples/example.diff
uv run code_review_run --diff samples/example.diff --repo-root ../some-checkout   # reviewers may read files
```
`samples/example.diff` has a SQL injection, a hard-coded key, `pickle.loads`, an untested function and a badly named one.

Run the webhook service:
```bash
uv run uvicorn code_review.api:app --host 0.0.0.0 --port 8080
curl -X POST http://localhost:8080/review -H "Content-Type: application/json" -H "X-GitHub-Event: pull_request" -d @samples/pr_event.json
curl -X POST http://localhost:8080/review/diff -H "Content-Type: application/json" -d "{\"title\":\"t\",\"diff\":\"...\"}"
```
`/review` answers `202` at once and reviews in the background (fetches the diff from GitHub, posts the comment when `GITHUB_TOKEN` is set). Set `GITHUB_WEBHOOK_SECRET` to verify `X-Hub-Signature-256`. `/review/diff` reviews a raw diff synchronously and returns the findings and the comment as JSON, so a Spring Boot app can call it.

Train and evaluate (the scripts call `Crew.train` / `Crew.test` on the sample diff; they have project-specific names so they do not collide with other projects in the shared venv):
```bash
uv run code_review_train -n 2 -f training.pkl     # interactive: you give feedback on each reviewer output
uv run code_review_test -n 2 -m anthropic/claude-sonnet-5-5   # model-graded scores 1-10; -m defaults to the configured LLM
```

Tests (offline, no model needed):
```bash
uv run --package code-review-agent pytest 03-code-review-agent/tests     # from the repository root
```

### Docker

The image installs from the workspace lock file, so the Docker build context is the **repository root**:

```bash
docker compose -f 03-code-review-agent/docker-compose.yml up --build    # from the repository root; http://localhost:8080
```
Compose reads `03-code-review-agent/.env`. For a local LLM from the container `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434` (Windows/macOS; on Linux run Ollama on the Docker network). Not built or run yet in this repository; the compose file is validated with `docker compose config`.

### Optional observability

Set `OTEL_EXPORTER_OTLP_ENDPOINT` in `.env` (any OTLP/HTTP backend, including Langfuse's OTLP endpoint; add its auth with the standard `OTEL_EXPORTER_OTLP_HEADERS`). Each review then produces one `review` span with title, file, chunk and finding counts. Leave it empty to disable.
