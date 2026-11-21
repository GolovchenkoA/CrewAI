# AGENTS.md

A learning repository for CrewAI: eight small projects in one uv workspace. Windows + PowerShell is the main environment.

## Layout

| Folder | What it is |
|---|---|
| `01-research-report-crew` | sequential crew that writes a research report |
| `02-support-ticket-triage-flow` | Flow with routing, FastAPI, MCP |
| `03-code-review-agent` | FastAPI webhook that reviews PRs with two crews; Docker, OpenTelemetry/Jaeger |
| `04-hierarchical-delegation` | hierarchical vs sequential process |
| `05-conditional-tasks` | `ConditionalTask` |
| `06-streaming` | streaming output |
| `07-standalone-calls` | LLM / Agent calls without a crew |
| `08-flow-checkpoint` | flow checkpoint and resume (no LLM) |

One shared `.venv` and one `uv.lock` live in the repository root. Each project has its own `pyproject.toml`, `.env.example` (copy to `.env`) and README with its run commands. Python is pinned by `.python-version` (3.12; crewai does not support 3.14).

## Commands (from the repository root)

- Install everything: `uv sync`. Do not use `uv sync --package <name>` for day-to-day work: it removes the other projects from the shared `.venv`.
- Tests, offline, no API key: `uv run --package <package-name> pytest <folder>/tests` (for example `--package code-review-agent` and `03-code-review-agent/tests`). Plain `uv run pytest` does not work.
- Lint: `uv run ruff check <files>` and `uv run ruff format <files>`. Run them only on files you changed: running `ruff format` on a whole project reformats unrelated files. Known ruff errors in older files are listed in `docs/todo_updates.md`.
- Docker (project 03): `docker compose -f 03-code-review-agent/docker-compose.yml up --build` from the root; add `--profile tracing` for Jaeger. A plain restart does not reload env vars: use `up -d --force-recreate`.

## Rules

- **Fetch english version from https://docs.crewai.com/llms.txt for CrewAI documentation and ignore other languages. It's the primary source of documentation**
- **Check crewai APIs before using them.** `Agent`, `Task` and `Crew` silently ignore unknown keyword arguments. Verify with `Task.model_fields` and read the `check-crewai-api` skill (`.claude/skills/`) first; the installed source wins over remembered docs.
- **Never commit or push.** The owner commits. Leave changes in the working tree.
- **Secrets:** `ANTHROPIC_API_KEY` is an operating-system environment variable. Never write it into `.env`, `.env.example`, compose files, images or logs. Leave it empty in `.env`; compose passes it through from the shell.
- **Dependencies are patch-pinned:** write `~=X.Y.Z` (patch updates only). `uv.lock` holds the exact versions. Upgrade deliberately with `uv lock --upgrade-package <name>`, then run all test suites.
- **Always set `max_tokens` on Claude models.** In `make_llm()` pass `max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))`. Without it crewai uses 128000 for Sonnet 5 and the `anthropic` SDK refuses the call with "Streaming is required for operations that may take longer than 10 minutes". Not needed when the LLM streams (project 06).
- **Do not remove the `anthropic` override in the root `pyproject.toml`** (`override-dependencies = ["anthropic~=2.12.0"]`). It replaces crewai's own pin `anthropic~=0.73.0`, which the OpenInference tracing packages in project 03 do not work with.
- **Tests stay offline:** use the stub LLM in `tests/stub_llm.py`; no test may call a real model or the network.
- When changing behaviour, update the project's README and `.env.example` in the same change.

## Style

Short, direct code and docs. Comments only for non-obvious reasons. Keep README examples runnable as written.
