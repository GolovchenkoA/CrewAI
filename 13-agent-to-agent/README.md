# 13 - Agent-to-agent (A2A) protocol

## 1. What the project does

Two separate processes that talk over the [A2A protocol](https://a2a-protocol.org/latest/):

```
terminal 1: a2a_serve                      terminal 2: a2a_ask "How many PLN for 250 EUR?"
  Currency desk (CrewAI agent)   <-- HTTP / JSON-RPC -->   Coordinator (CrewAI agent)
  tool: exchange_rate                                       no exchange rates of its own
  http://127.0.0.1:9999                                     reads the server's agent card
```

- **Server** (`server.py`): a normal CrewAI agent with `a2a=A2AServerConfig(url=...)`. It has one tool with **made-up desk rates** (1 EUR = 4.27 PLN), so a correct answer proves the client really asked the server.
- **Client** (`client.py`): a coordinator agent with `a2a=A2AClientConfig(endpoint=<agent card URL>)`. It decides on its own whether to answer or to delegate to the remote agent.

Live result (`qwen3:4b` on both sides):

```
answer: 250 EUR is equivalent to 1,067.50 PLN based on the current exchange rate of 1 EUR = 4.27 PLN.
```

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `Agent(a2a=A2AServerConfig(url=...))`: the agent can describe itself | `server.py` (`build_server_agent`) |
| The agent card is generated for you: `agent.to_agent_card(url)`; the tool became the skill `exchange_rate` | `server.py` (`build_app`) |
| Hosting it: an a2a-sdk `AgentExecutor` that calls `crewai.a2a.utils.task.execute`, served by uvicorn | `server.py` (`CrewAIExecutor`) |
| `Agent(a2a=A2AClientConfig(endpoint=..., max_turns=...))`: delegation to a remote agent | `client.py` |
| Offline tests: agent card, a full JSON-RPC request into the server (in-process, no socket), client config | `tests/test_a2a.py` |

Things worth knowing (crewai 1.15.44, a2a-sdk 0.3.26):

- **Needs the extra**: `crewai[a2a]` (this project's `pyproject.toml` has it).
- **The docs show only half of the server.** They show `A2AServerConfig` on an agent but not how to serve it. In open source you add the HTTP side yourself, as in `server.py` (about 20 lines). On CrewAI AMP the platform hosts it.
- **The client decides.** With `A2AClientConfig` the agent chooses between answering itself and delegating, based on the agent card. Small models may answer from memory; the made-up rates make that visible.
- **The agent card is the contract**: name, description, skills (derived from the agent's tools) and the URL, served at `/.well-known/agent-card.json`. Without a card the client cannot connect (`fail_fast=True` raises; set `fail_fast=False` to continue without the remote agent).
- **No authentication here.** The server listens on `127.0.0.1` only. `auth=` on the client and server configs supports bearer tokens, OAuth2, API keys and more; use one before exposing a port.
- `A2AConfig` is deprecated; use `A2AClientConfig` and `A2AServerConfig`.
- Do not mix up A2A with **delegation inside one crew** (`allow_delegation=True`, project 04): that stays in one process and uses CrewAI's own tools. A2A crosses a process or machine boundary and works with agents that are not built with CrewAI.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 13-agent-to-agent
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo).

Run, from `13-agent-to-agent/`, in **two terminals**:

```bash
uv run a2a_serve                        # terminal 1: the server; check http://127.0.0.1:9999/.well-known/agent-card.json
```

```bash
uv run a2a_ask                          # terminal 2: the client with the default question
uv run a2a_ask "How many USD is 100 EUR?"
```

Stop the server with Ctrl+C. Change the port with `A2A_PORT` in `.env`.

Tests (offline, no model and no real network), from the repository root:

```bash
uv run --package agent-to-agent pytest 13-agent-to-agent/tests
```
