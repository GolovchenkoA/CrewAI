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
| LiteLLM, Claude / local switch | `llm_factory.py` |

The MCP server is written in Python (FastMCP) so the project runs without extra tooling. Because you work with Spring Boot, the README of `mcp_server/` also describes swapping it for a Spring AI MCP server that exposes the same tools (`get_ticket`, `search_orders`, `get_customer`).

## 3. Prepare, build, run

Requirements: Python **3.12 or 3.13** (CrewAI 1.15.x requires `>=3.10,<3.14`), an Anthropic API key **or** Ollama.

### Create the virtual environment and install

**Windows (PowerShell)**
```powershell
cd 02-support-ticket-triage-flow
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux / macOS**
```bash
cd 02-support-ticket-triage-flow
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

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

```bash
crewai flow kickoff                                   # runs sample tickets in data/tickets/
python -m triage_flow.main --ticket data/tickets/billing_01.json
crewai flow plot                                      # writes flow diagram HTML
```

The MCP server is started automatically over stdio by the flow. To run it by hand: `python mcp_server/ticket_server.py`.

> Use Claude for the classifier/router if the local model misclassifies; routing quality depends heavily on structured-output reliability.
