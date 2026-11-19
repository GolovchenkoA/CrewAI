# 02 - Support Ticket Triage Flow

## 1. What the project does

An event-driven **Flow** that triages incoming support tickets:

1. Ingests a ticket (JSON from a file or a small REST endpoint).
2. A classifier crew labels it `billing`, `bug` or `how-to` and returns a confidence score.
3. A router sends it to the matching specialist crew. Each specialist answers using product docs (RAG) and ticket data from an **MCP server**.
4. Low confidence (< threshold) pauses the flow and asks a human to approve or edit the answer.
5. Memory recognises repeat customers and reuses earlier context.

Output: a draft reply and a ticket record in `output/`.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| **Flows**: `@start`, `@listen`, `@router`, `and_` / `or_` | `flow.py` |
| Typed Flow state (Pydantic `BaseModel`) | `TicketState` |
| Crews embedded in Flow steps | classifier + 3 specialist crews |
| Parallel branches | sentiment + classification run concurrently |
| **MCP tools** (stdio server, `MCPServerAdapter`) | `mcp_server/ticket_server.py` |
| **Knowledge** (RAG over docs in `knowledge/`) | specialists |
| **Memory**: short-term, long-term, entity | repeat-customer recognition |
| Human-in-the-loop (`human_input`, flow `input`) | low-confidence escalation |
| Structured output (`output_pydantic`) | classification result |
| Flow persistence (`@persist`) | resume after restart |
| Flow plot (`flow.plot()`) | architecture diagram |
| Claude / local LLM switch (native providers) | `llm_factory.py` |

The MCP server is written in Python (FastMCP) so the project runs without extra tooling. Because you work with Spring Boot, the README of `mcp_server/` also describes swapping it for a Spring AI MCP server that exposes the same tools (`get_ticket`, `search_orders`, `get_customer`).

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root: one shared `.venv` and one `uv.lock` for all three projects. For first-time setup on a new computer (installing uv, Ollama, cloning) see the [root README](../README.md#setting-up-on-another-computer).

Requirements: [uv](https://docs.astral.sh/uv/) (it downloads Python 3.12 automatically, pinned by the root `.python-version`; CrewAI 1.15.x does not support Python 3.14), and an Anthropic API key **or** Ollama.

### Install dependencies

Run `uv sync` once from the **repository root**, then create this project's `.env`.

**Windows (PowerShell)**
```powershell
cd <repo-root>
uv sync                                  # or: uv sync --package support-ticket-triage-flow
cd 02-support-ticket-triage-flow
Copy-Item .env.example .env
```

**Linux / macOS**
```bash
cd <repo-root>
uv sync                                  # or: uv sync --package support-ticket-triage-flow
cd 02-support-ticket-triage-flow
cp .env.example .env
```

No manual activation is needed; prefix commands with `uv run`. To activate the shared environment anyway: `..\.venv\Scripts\Activate.ps1` (Windows) or `source ../.venv/bin/activate` (Linux).

### Choose the LLM and embeddings (edit `.env`)

Claude (`LLM_PROVIDER=claude`, set `ANTHROPIC_API_KEY`). Claude has no embedding model, so Memory and Knowledge always use a local embedder:

```bash
ollama pull mxbai-embed-large     # embeddings for Memory / Knowledge
ollama pull qwen3.5:9b            # local LLM (~6.6 GB, fits 8 GB VRAM)
```

Local (`LLM_PROVIDER=local`): start Ollama with a larger context:

- Windows: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
- Linux: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

### Run

From `02-support-ticket-triage-flow/`:
```bash
uv run crewai flow kickoff                                # runs sample tickets in data/tickets/
uv run python -m triage_flow.main --ticket data/tickets/billing_01.json
uv run crewai flow plot                                   # writes flow diagram HTML
```

The MCP server is started automatically over stdio by the flow. To run it by hand: `uv run python mcp_server/ticket_server.py`.

> Use Claude for the classifier/router if the local model misclassifies; routing quality depends heavily on structured-output reliability.
