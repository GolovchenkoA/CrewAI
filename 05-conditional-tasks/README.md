# 05 - Conditional tasks

## 1. What the project does

The smallest possible demo of CrewAI's **`ConditionalTask`**. An incident report goes through three tasks:

1. **Triage** always runs and returns a structured result (`severity` low or high, plus a summary).
2. **Deep dive** is a `ConditionalTask`: it runs only when the triage says `high`.
3. **Status update** always runs and uses whatever the earlier tasks produced.

A low-severity incident never calls the investigator model, so you save the expensive step.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `ConditionalTask` with a `condition` function on the previous `TaskOutput` | `crew.py` |
| Structured output (`output_pydantic`) that the condition reads | `models.py`, `crew.py` |
| `context=[...]` on the final task, including a task that may have been skipped | `crew.py` |
| Claude / local LLM switch (native providers) | `llm_factory.py` |
| Offline test of both branches with a stub LLM | `tests/test_crew.py` |

Things worth knowing:

- A skipped conditional task still appears in `result.tasks_output`, with an **empty `raw`**. That is how `main.py` tells "skipped" from "ran".
- The condition receives only the output of the task directly before it, and a `ConditionalTask` cannot be the first task or be async.
- The condition is fail-safe: if the model returned no valid structure (`pydantic` is `None`), it investigates anyway.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 05-conditional-tasks
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo).

Run, from `05-conditional-tasks/`:

```bash
uv run conditional_run --sample high      # deep dive runs
uv run conditional_run --sample low       # deep dive is skipped
uv run conditional_run --incident "Login page is slow for some users"
```

Tests (offline, no model needed), from the repository root:

```bash
uv run --package conditional-tasks pytest 05-conditional-tasks/tests
```
