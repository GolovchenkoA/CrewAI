# CrewAI Learning Projects

Three hands-on projects that together cover the main aspects of [CrewAI](https://docs.crewai.com). They form one [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): a single shared virtual environment (`.venv`) and a single lock file (`uv.lock`) in this folder, so dependencies are downloaded once, not per project.

All projects use Python 3.12 (CrewAI 1.15.x does not support 3.14) and can switch between Claude and a local Ollama model via LiteLLM with `LLM_PROVIDER=claude|local`.

| Project | What it does | Main CrewAI topics |
|---|---|---|
| [01-research-report-crew](01-research-report-crew/README.md) | Four agents (researcher, analyst, writer, editor) turn a topic into a Markdown report. | Agents, tasks, crews, YAML config, sequential and hierarchical process, tools, structured output, guardrails, async tasks |
| [02-support-ticket-triage-flow](02-support-ticket-triage-flow/README.md) | An event-driven flow classifies support tickets, routes them to specialist crews and escalates to a human when confidence is low. | Flows, routers, typed state, MCP tools, Knowledge (RAG), Memory, human-in-the-loop |
| [03-code-review-agent](03-code-review-agent/README.md) | A webhook service where security, style and test reviewers review pull requests and post a summary. | Planning, train and test, event listeners, observability, cost tracking, batch runs, Docker deployment |

Suggested order: 01 teaches the vocabulary, 02 the architecture, 03 the operations.

## Status

Workspace, dependencies and documentation are in place. The Python code of the projects is not implemented yet: each `src/<package>/` is an empty skeleton. Once a project has its scaffold (`crewai create`), add a `[project.scripts]` entry point so `crewai run` / `crewai flow kickoff` can start it.

## Repository layout

```
.
├── pyproject.toml            # uv workspace root (lists the members)
├── uv.lock                   # one lock file for all projects (commit it)
├── .python-version           # 3.12, picked up by uv automatically
├── .venv/                    # shared environment (git-ignored, created by `uv sync`)
├── 01-research-report-crew/  # pyproject.toml, .env.example, src/research_crew/
├── 02-support-ticket-triage-flow/   # ... src/triage_flow/
└── 03-code-review-agent/            # ... src/code_review/
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

`uv sync --locked` creates `.venv` in the repo root and installs exactly the versions in `uv.lock` for all three projects. Use plain `uv sync` if you want it to update the lock file when dependencies change. To install only one project: `uv sync --package research-report-crew` (other names: `support-ticket-triage-flow`, `code-review-agent`).

### 3. Configure each project

**Windows (PowerShell)**
```powershell
Copy-Item 01-research-report-crew\.env.example 01-research-report-crew\.env
Copy-Item 02-support-ticket-triage-flow\.env.example 02-support-ticket-triage-flow\.env
Copy-Item 03-code-review-agent\.env.example 03-code-review-agent\.env
```

**Linux / macOS**
```bash
for p in 01-research-report-crew 02-support-ticket-triage-flow 03-code-review-agent; do cp $p/.env.example $p/.env; done
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
