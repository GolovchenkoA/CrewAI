# 01 - Research & Report Crew

## 1. What the project does

A crew of four agents that takes a topic (e.g. "LangGraph vs CrewAI") and produces a Markdown report.

`Researcher -> Analyst -> Writer -> Editor`

- **Researcher** gathers facts (web search + local notes folder).
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
| Built-in tools (`SerperDevTool` or `DuckDuckGoSearchRun`, `FileReadTool`, `DirectoryReadTool`) | Researcher |
| Custom tool (`@tool`) | `tools/word_count.py` |
| Structured output (`output_pydantic`) | Analyst |
| Async tasks (`async_execution`) | parallel research subtopics |
| Task guardrails | Editor output validation |
| Per-agent LLM config (LiteLLM), Claude / local switch | `llm_factory.py` |
| `crewai create`, `crewai run`, `kickoff_for_each` | CLI + batch topics |

## 3. Prepare, build, run

Requirements: Python **3.12 or 3.13** (CrewAI 1.15.x requires `>=3.10,<3.14`; 3.14 is not supported yet), Git, and either an Anthropic API key or [Ollama](https://ollama.com) for a local model.

### Create the virtual environment and install

**Windows (PowerShell)**
```powershell
cd 01-research-report-crew
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux / macOS**
```bash
cd 01-research-report-crew
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

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

```bash
crewai run                       # uses TOPIC from .env
python -m research_crew.main --topic "LangGraph vs CrewAI"
```
Results are written to `output/`. To run the hierarchical variant set `PROCESS=hierarchical` in `.env`.

> Small local models are weaker at tool calling and delegation. If the hierarchical run loops, use Claude for the manager agent (`MANAGER_LLM_PROVIDER=claude`).
