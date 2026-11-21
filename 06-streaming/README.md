# 06 - Streaming

## 1. What the project does

The smallest possible demo of CrewAI **streaming**: print the answer while the model is still writing it, instead of waiting for the whole result.

- **crew mode**: one agent, one task, `Crew(stream=True)`. You iterate over the chunks, then read the normal result.
- **flow mode**: a two-step flow with `stream=True`. The stream carries flow events and the model's text.
- **compare mode**: the same crew without streaming, to see how long the first output takes.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `Crew(stream=True)`: `kickoff()` returns a `CrewStreamingOutput` you iterate over | `crew.py`, `main.py` |
| `.result` of the stream: the normal `CrewOutput`, available after the last chunk | `main.py` |
| `Flow(stream=True)`: the stream yields `StreamFrame` events (`method_execution_started`, `llm_call_started`, ...) and the text | `flow.py`, `main.py` |
| `LLM(stream=True)`: the model sends tokens as they are made | `llm_factory.py` |
| Claude / local LLM switch (native providers) | `llm_factory.py` |
| Offline tests with a stub LLM | `tests/test_streaming.py` |

Things worth knowing:

- Crew streaming turns on the model's streaming itself. In a flow you must make the **LLM** stream (`llm_stream=True` in this project), otherwise the flow stream carries only events and no text.
- Iterating the stream is what runs the work: the loop blocks until the next chunk and ends when the run is done. Read `.result` only after the loop.
- Measured on `qwen3:4b`: the crew stream gave 179 chunks and the first one after 6.4 s. The whole answer takes longer, so streaming improves how fast the run *feels*, not how long it takes.
- A flow stream mixes event frames and text. `main.py` prints the text as is and the events as `· event_name` markers.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 06-streaming
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo).

Run, from `06-streaming/`:

```bash
uv run streaming_run --mode crew        # text appears as it is written
uv run streaming_run --mode flow        # events and text
uv run streaming_run --mode compare     # no streaming: one block at the end
uv run streaming_run --topic "black holes"
```

Tests (offline, no model needed), from the repository root:

```bash
uv run --package streaming pytest 06-streaming/tests
```
