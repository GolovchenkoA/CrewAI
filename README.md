# CrewAI Learning Projects

10 hands-on projects that together cover the main aspects of [CrewAI](https://docs.crewai.com). They form one [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): a single shared virtual environment (`.venv`) and a single lock file (`uv.lock`) in this folder, so dependencies are downloaded once, not per project.

All projects use Python 3.12 (CrewAI 1.15.x does not support 3.14) and can switch between Claude and a local Ollama model with `LLM_PROVIDER=claude|local`.

| Project | What it does | Main CrewAI topics |
|---|---|---|
| [01-research-report-crew](01-research-report-crew/README.md) | Four agents (researcher, analyst, writer, editor) turn a topic into a Markdown report. | Agents, tasks, crews, YAML config, sequential and hierarchical process, tools, structured output, guardrails, async tasks |
| [02-support-ticket-triage-flow](02-support-ticket-triage-flow/README.md) | An event-driven flow classifies support tickets, routes them to specialist crews and escalates to a human when confidence is low. | Flows, routers, typed state, MCP tools, Knowledge (RAG), Memory, human-in-the-loop |
| [03-code-review-agent](03-code-review-agent/README.md) | A webhook service where security, style and test reviewers review pull requests and post a summary. | Planning, train and test, event listeners, observability, cost tracking, batch runs, Docker deployment |
| [04-hierarchical-delegation](04-hierarchical-delegation/README.md) | A manager agent delegates two tasks to a researcher and a writer. Minimal demo. | Hierarchical process, manager agent, delegation |
| [05-conditional-tasks](05-conditional-tasks/README.md) | An incident is triaged; a deep dive runs only for high severity. Minimal demo. | `ConditionalTask`, structured output |
| [06-streaming](06-streaming/README.md) | Prints crew and flow output while the model is still writing it. Minimal demo. | `stream=True` for crews, flows and LLMs |
| [07-standalone-calls](07-standalone-calls/README.md) | `LLM.call` and `Agent.kickoff` with a tool and structured output, no crew. Minimal demo. | Standalone LLM and agent calls |
| [08-flow-checkpoint](08-flow-checkpoint/README.md) | A three-step flow fails in step 2 and the rerun resumes from the checkpoint without repeating step 1. Minimal demo, no model needed. | Flow checkpointing, `from_checkpoint` |
| [09-conversational-flow](09-conversational-flow/README.md) | A console chat: one `handle_turn` call per message, state kept per session id. Minimal demo. | Conversational flow (experimental) |
| [10-agent-reasoning](10-agent-reasoning/README.md) | The same task with and without agent planning; prints the plan and the cost. Minimal demo. | `planning_config` (agent reasoning) |

Suggested order: 01 teaches the vocabulary, 02 the architecture, 03 the operations. 04 to 10 are small single-feature demos (see [FUTURE_PROJECTS.md](FUTURE_PROJECTS.md) for the planned ones).

## Status

All 10 projects are implemented and covered by offline tests (stub LLM, no key needed). Each project has its own script names (`research_crew_*`, `triage_flow_*`, `code_review_*`, `hierarchical_run`, `conditional_run`, `streaming_run`, `standalone_run`, `checkpoint_run`, `chat_run`, `reasoning_run`), so they do not collide in the shared venv; see the project READMEs. Runs against real models (Claude, local Ollama) were done for 01 and 02; project 03 has only been tested offline so far; 04 to 07 and 09 were also run against `qwen3:4b`, 10 against `qwen3.5:9b` (smaller models were not reliable for planning); 08 needs no model and was run as a CLI.

## Repository layout

```
.
├── pyproject.toml            # uv workspace root (lists the members)
├── uv.lock                   # one lock file for all projects (commit it)
├── .python-version           # 3.12, picked up by uv automatically
├── .venv/                    # shared environment (git-ignored, created by `uv sync`)
├── 01-research-report-crew/  # pyproject.toml, .env.example, src/research_crew/
├── 02-support-ticket-triage-flow/   # ... src/triage_flow/
├── 03-code-review-agent/            # ... src/code_review/
├── 04-hierarchical-delegation/      # ... src/hierarchical_delegation/
├── 05-conditional-tasks/            # ... src/conditional_tasks/
├── 06-streaming/                    # ... src/streaming_demo/
├── 07-standalone-calls/             # ... src/standalone_calls/
├── 08-flow-checkpoint/              # ... src/flow_checkpoint/
├── 09-conversational-flow/          # ... src/conversational_flow/
└── 10-agent-reasoning/              # ... src/agent_reasoning/
```

Each project keeps its own `.env` (git-ignored). Copy `.env.example` to `.env` and fill in your keys.

## Setting up on another computer

### 1. Prerequisites

| Tool | Needed for | Install |
|---|---|---|
| Git | cloning the repo | https://git-scm.com |
| uv | Python + dependencies | see below |
| Ollama | local LLM and embeddings (optional if you only use Claude, except projects 02 and 03 memory/knowledge need `mxbai-embed-large`) | https://ollama.com |
| Docker | project 03 container (optional) | https://docs.docker.com/get-docker/ |

You do **not** need to install Python yourself: uv reads `.python-version` and downloads Python 3.12 if it is missing.

Install uv:

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Open a new terminal afterwards and check with `uv --version`.

### 2. Clone and install the workspace

```bash
git clone <repository-url> CrewAI
cd CrewAI
uv sync --locked
```

`uv sync --locked` creates `.venv` in the repo root and installs exactly the versions in `uv.lock` for all projects. Use plain `uv sync` if you want it to update the lock file when dependencies change. To install only one project: `uv sync --package research-report-crew` (other names: `support-ticket-triage-flow`, `code-review-agent`, `hierarchical-delegation`, `conditional-tasks`, `streaming`, `standalone-calls`).

### 3. Configure each project

**Windows (PowerShell)**
```powershell
Copy-Item 01-research-report-crew\.env.example 01-research-report-crew\.env
Copy-Item 02-support-ticket-triage-flow\.env.example 02-support-ticket-triage-flow\.env
Copy-Item 03-code-review-agent\.env.example 03-code-review-agent\.env
Copy-Item 04-hierarchical-delegation\.env.example 04-hierarchical-delegation\.env
Copy-Item 05-conditional-tasks\.env.example 05-conditional-tasks\.env
Copy-Item 06-streaming\.env.example 06-streaming\.env
Copy-Item 07-standalone-calls\.env.example 07-standalone-calls\.env
Copy-Item 08-flow-checkpoint\.env.example 08-flow-checkpoint\.env
Copy-Item 09-conversational-flow\.env.example 09-conversational-flow\.env
Copy-Item 10-agent-reasoning\.env.example 10-agent-reasoning\.env
```

**Linux / macOS**
```bash
for p in 01-research-report-crew 02-support-ticket-triage-flow 03-code-review-agent 04-hierarchical-delegation 05-conditional-tasks 06-streaming 07-standalone-calls 08-flow-checkpoint 09-conversational-flow 10-agent-reasoning; do cp $p/.env.example $p/.env; done
```

Edit each `.env`: set `LLM_PROVIDER=claude` and `ANTHROPIC_API_KEY`, or `LLM_PROVIDER=local`. `.env` files are never committed; API keys must be entered again on every computer.

### 4. Local models (30 GB RAM, 8 GB VRAM GPU)

```bash
ollama pull qwen3.5:9b            # ~6.6 GB, fits in 8 GB VRAM
ollama pull mxbai-embed-large     # embeddings for Memory / Knowledge
```
Start Ollama with a larger context window (the default 4096 is too small for CrewAI):

- Windows: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
- Linux: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

### 5. Run a project

Work inside the project folder and prefix commands with `uv run` (no activation needed):

```bash
cd 01-research-report-crew
uv run crewai run
```

To activate the shared environment instead: `.\.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (Linux).

### Common tasks

| Task | Command (from repo root) |
|---|---|
| Add a dependency to one project | `uv add --package research-report-crew <package>` |
| Upgrade everything (e.g. newer CrewAI) | `uv lock --upgrade && uv sync` |
| Rebuild the environment from scratch | delete `.venv`, then `uv sync --locked` |
| Check which Python is used | `uv run python --version` |

Troubleshooting: if uv picks Python 3.14, run `uv python install 3.12` and delete `.venv`; CrewAI 1.15.x requires Python below 3.14.
