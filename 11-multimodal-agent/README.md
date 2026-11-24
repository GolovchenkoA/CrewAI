# 11 - Multimodal agent (image input)

## 1. What the project does

An agent answers a question about an image. The sample is `samples/sales_chart.png`, a bar chart of quarterly sales (Q1 30, Q2 45, Q3 60, Q4 20).

```
question + image path -> text agent -> look_at_image tool -> vision model -> answer
```

The agent runs on a text model that supports tool calls. The tool sends the image to a **vision model** as an `image_url` content block (a base64 data URL inside a normal chat message) and returns the answer as text. With `LLM_PROVIDER=claude` one Claude model plays both roles.

```
answer: The quarter with the highest value is Q3, with 60 units sold.
```

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| An image in a chat message: `{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}` | `vision.py` (`image_message`) |
| A custom `@tool` that calls a second LLM | `vision.py` (`make_vision_tool`) |
| `Agent.kickoff()` with a tool | `agent.py` |
| Separate models for the agent and for vision | `llm_factory.py` (`make_llm(vision=True)`), `.env` (`VISION_MODEL`) |
| Offline tests: a stub vision model checks that the image block reaches it | `tests/test_vision.py` |

### Why a vision tool and not the image straight into the agent

I tried the direct routes on crewai 1.15.44 with a local `qwen2.5vl:7b`:

| Route | Result |
|---|---|
| `LLM.call(messages_with_image_block)` | works (this is what the tool does) |
| `Agent.kickoff([message_with_image_block])` | the image is dropped; the model **invents** an answer ("Q4, 120") |
| `Agent(multimodal=True)` (adds `AddImageTool`) | deprecated, and `qwen2.5vl` does not support tool calls, so it invents an answer too |
| `Agent.kickoff(..., input_files={"chart": ImageFile(...)})` (`crewai[file-processing]`) | the official way, but the Ollama provider reports `supports_multimodal() == False`, so files are rejected, and the extra needs `python-magic`, whose import hung on this Windows machine |

So: **a vision model usually cannot be the agent** (it often has no tool calling), and the agent path may silently lose the image. A tool keeps both parts reliable. With a native vision model such as Claude and `crewai[file-processing]` installed, `input_files` is the more direct option.

Other things worth knowing:

- Always check the answer against the image. A model that did not receive the image still answers confidently.
- The Anthropic provider converts `image_url` blocks to its own image format, so the same tool works with Claude.
- Large images cost tokens (the sample is about 1100 prompt tokens). Resize big screenshots first.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 11-multimodal-agent
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (the agent) and `ollama pull qwen2.5vl:7b` (vision, 6 GB). The default local model of the other projects cannot read images.

Run, from `11-multimodal-agent/`:

```bash
uv run multimodal_run
uv run multimodal_run --image samples/sales_chart.png --question "Which quarter has the lowest value?"
```

Tests (offline, no model needed), from the repository root:

```bash
uv run --package multimodal-agent pytest 11-multimodal-agent/tests
```
