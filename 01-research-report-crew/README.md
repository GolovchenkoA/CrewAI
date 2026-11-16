# 01 - Research & Report Crew

## 1. What the project does

A crew of five agents that takes a topic (e.g. "LangGraph vs CrewAI") and produces a Markdown report.

```
Notes Researcher ─┐ (parallel)
                  ├─> Analyst -> Writer -> Editor
Web Scout ────────┘
```

- **Notes Researcher** reads the local `notes/` folder (`DirectoryReadTool`, `FileReadTool`).
- **Web Scout** scrapes the pages listed in `SOURCE_URLS` (`ScrapeWebsiteTool`).
- **Analyst** merges both findings into a structured list of claims with confidence (Pydantic).
- **Writer** drafts the report from the analysis.
- **Editor** polishes it and checks length with a custom *Word Count* tool; a guardrail rejects the result until it has the headings *Executive Summary*, *Key Findings*, *Conclusion*, *Sources* and enough words.

Output per topic: `output/<topic-slug>/report.md` and `output/<topic-slug>/analysis.json`
(for example `output/langgraph-vs-crewai/report.md`).

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| Agents (role, goal, backstory) | `config/agents.yaml` |
| Tasks, task `context` chaining | `config/tasks.yaml` |
| YAML config + `@CrewBase` decorators | `crew.py` |
| Sequential process, then hierarchical process with a manager agent | `PROCESS` env switch (`MANAGER_LLM_PROVIDER` for the manager) |
| Delegation (`allow_delegation`) | Notes Researcher / Editor (`ALLOW_DELEGATION`) |
| Built-in tools (`ScrapeWebsiteTool`, `FileReadTool`, `DirectoryReadTool`) | Web Scout, Notes Researcher |
| Custom tool (`@tool`) | `tools/word_count.py` (Editor) |
| Structured output (`output_pydantic`), output files | `models.py`, Analyst -> `analysis.json` |
| Async tasks (`async_execution`) | the two research tasks run in parallel (sequential process only) |
| Task guardrails with retry | `guardrails.py`, Editor output |
| One LLM object per agent, Claude / local switch | `llm_factory.py` |
| Batch runs (`kickoff_for_each`) | `--topics "a;b;c"` |
| Offline tests with a stub LLM | `tests/` |

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root: one shared `.venv` and one `uv.lock` for all three projects. For first-time setup on a new computer (installing uv, Ollama, cloning) see the [root README](../README.md#setting-up-on-another-computer).

Requirements: [uv](https://docs.astral.sh/uv/) (it downloads Python 3.12 automatically, pinned by the root `.python-version`; CrewAI 1.15.x does not support Python 3.14), and either an Anthropic API key or [Ollama](https://ollama.com) for a local model.

### Install dependencies

Run `uv sync` once from the **repository root** (creates `<root>/.venv` for all projects), then create this project's `.env`.

**Windows (PowerShell)**
```powershell
cd <repo-root>
uv sync                                  # or: uv sync --package research-report-crew
cd 01-research-report-crew
Copy-Item .env.example .env
```

**Linux / macOS**
```bash
cd <repo-root>
uv sync                                  # or: uv sync --package research-report-crew
cd 01-research-report-crew
cp .env.example .env
```

No manual activation is needed; prefix commands with `uv run`. To activate the shared environment anyway: `..\.venv\Scripts\Activate.ps1` (Windows) or `source ../.venv/bin/activate` (Linux).

### Choose the LLM (edit `.env`)

Claude:
```
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

Local (fits 30 GB RAM + 8 GB VRAM GPU):
```
LLM_PROVIDER=local
```
```bash
ollama pull qwen3.5:9b        # ~6.6 GB, fits fully in 8 GB VRAM
# ollama pull llama3.1:8b     # alternative
```
Start Ollama with a larger context, because the default (4096) is too small for CrewAI prompts:

- Windows: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
- Linux: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

### Run

From `01-research-report-crew/`:
```bash
uv run research_crew_run                                  # topic from TOPIC in .env
uv run research_crew_run --topic "LangGraph vs CrewAI" --urls "https://docs.crewai.com/en/introduction"
uv run research_crew_run --topics "LangGraph;AutoGen;CrewAI"   # batch, one report per topic
uv run research_crew_train 3 training.pkl                 # crewai train equivalent
uv run research_crew_test 2 anthropic/claude-sonnet-5-5   # crewai test equivalent (real model, costs money)
```
Results are written to `output/<topic-slug>/report.md` and `analysis.json`. Put your own notes (Markdown/text) into `notes/`; the Notes Researcher reads only that folder (`NOTES_DIR`). To run the hierarchical variant set `PROCESS=hierarchical` in `.env`.

Settings in `.env` (see `.env.example`): `LLM_PROVIDER`, `PROCESS`, `ALLOW_DELEGATION`, `SOURCE_URLS`, `NOTES_DIR`, `MIN_REPORT_WORDS`, `LLM_TIMEOUT`, `VERBOSE`.

> `crewai run` / `crewai train` are not used here: they call fixed script names (`run_crew`, `train`) that would collide between the projects of the shared workspace, so each project has its own `research_crew_*` scripts.

> Small local models are weaker at tool calling and delegation. If the hierarchical run loops or a run is slow, set `ALLOW_DELEGATION=false`, or use Claude for the manager agent (`MANAGER_LLM_PROVIDER=claude`).

### Tests (offline, no API key)

The tests use a stub LLM, so they need no model and no network:
```bash
uv run --package research-report-crew pytest 01-research-report-crew/tests   # from the repo root
```
