# 01 - Research & Report Crew

## 1. What the project does

A crew of four agents that takes a topic (e.g. "LangGraph vs CrewAI") and produces a Markdown report.

`Researcher -> Analyst -> Writer -> Editor`

- **Researcher** gathers facts by scraping the pages listed in `SOURCE_URLS` and reading a local notes folder.
- **Analyst** compares findings and extracts a structured list of claims (Pydantic).
- **Writer** drafts the report from the analysis.
- **Editor** checks the draft, and a guardrail rejects it until it has the required sections.

Output: `output/report.md` plus `output/analysis.json`.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| Agents (role, goal, backstory) | `config/agents.yaml` |
| Tasks, task `context` chaining | `config/tasks.yaml` |
| YAML config + `@CrewBase` decorators | `crew.py` |
| Sequential process, then hierarchical process with a manager agent | `PROCESS` env switch |
| Delegation (`allow_delegation`) | Researcher / Editor |
| Built-in tools (`ScrapeWebsiteTool`, `FileReadTool`, `DirectoryReadTool`) | Researcher |
| Custom tool (`@tool`) | `tools/word_count.py` |
| Structured output (`output_pydantic`) | Analyst |
| Async tasks (`async_execution`) | parallel research subtopics |
| Task guardrails | Editor output validation |
| Per-agent LLM config (LiteLLM), Claude / local switch | `llm_factory.py` |
| `crewai run`, `kickoff_for_each` | CLI + batch topics |

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
uv run crewai run                                         # uses TOPIC from .env
uv run python -m research_crew.main --topic "LangGraph vs CrewAI"
```
Results are written to `output/`. To run the hierarchical variant set `PROCESS=hierarchical` in `.env`.

> Small local models are weaker at tool calling and delegation. If the hierarchical run loops, use Claude for the manager agent (`MANAGER_LLM_PROVIDER=claude`).
