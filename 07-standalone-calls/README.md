# 07 - Standalone agent and LLM calls

## 1. What the project does

CrewAI without a `Crew`. One script with three small examples, from the lowest level up:

1. **`LLM.call(prompt)`**: a plain model call that returns text.
2. **`LLM.call(messages, response_model=City)`**: a model call that returns a validated Pydantic object.
3. **`Agent.kickoff(prompt, response_format=WordReport)`**: one agent with a tool, no task and no crew. It returns a `LiteAgentOutput` with `.raw` and `.pydantic`.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `LLM.call()` for plain text | `examples.py` (`plain_call`) |
| Structured output from a direct call (`response_model`) | `examples.py` (`structured_call`) |
| `Agent.kickoff()` with a tool and `response_format` | `examples.py` (`agent_with_tool`) |
| A custom tool with `@tool` | `examples.py` (`word_counter`) |
| Claude / local LLM switch (native providers) | `llm_factory.py` |
| Offline tests with a stub LLM, including the tool loop | `tests/test_examples.py` |

Things worth knowing:

- The two structured-output parameters have different names: `LLM.call(..., response_model=...)` but `Agent.kickoff(..., response_format=...)`. Using the wrong one raises a `TypeError`.
- `Agent.kickoff()` does **not** use the agent's `knowledge_sources`. For knowledge, run the agent as a task in a crew (see project 02) or put the facts in the prompt.
- Use these calls for one-off jobs (classify a text, extract fields). Use a crew when several agents or tasks depend on each other.
- `Agent.kickoff()` prints its own console panels (started, tool execution, completed). They are CrewAI's event output, not part of the result.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 07-standalone-calls
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo).

Run, from `07-standalone-calls/`:

```bash
uv run standalone_run                      # all three examples
uv run standalone_run --example structured # or: llm, agent
```

Tests (offline, no model needed), from the repository root:

```bash
uv run --package standalone-calls pytest 07-standalone-calls/tests
```
