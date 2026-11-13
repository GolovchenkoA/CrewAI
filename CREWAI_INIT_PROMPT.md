# CrewAI workspace init prompt

Paste everything below the line into your coding agent (Claude Code or similar), opened in the repository root. The prompt is idempotent: running it again on a configured machine only reports what is already done.

---

You are setting up this repository on the current computer so I can build and run CrewAI projects. Work from the repository root (the folder that contains `pyproject.toml` with `[tool.uv.workspace]`). Follow the steps in order, report the result of each step in one line, and stop to ask me before anything marked **ASK**.

## Project facts (do not change these)

- This is a **uv workspace**: one shared `.venv` and one `uv.lock` in the root, three members:
  - `01-research-report-crew` (package `research-report-crew`, code in `src/research_crew`)
  - `02-support-ticket-triage-flow` (package `support-ticket-triage-flow`, code in `src/triage_flow`)
  - `03-code-review-agent` (package `code-review-agent`, code in `src/code_review`)
- Python is pinned by `.python-version` to **3.12**. CrewAI 1.15.x requires Python `>=3.10,<3.14`, so Python 3.14 must never be used.
- Dependencies live in each `pyproject.toml` and in the root `uv.lock`. There are **no** `requirements.txt` files; do not create any.
- LLMs are switched per project with `LLM_PROVIDER=claude|local` in that project's `.env`, via LiteLLM:
  - Claude: `anthropic/claude-sonnet-5-5`, needs `ANTHROPIC_API_KEY`.
  - Local: Ollama model `ollama/qwen3.5:9b` (fits 8 GB VRAM, 30 GB RAM machine). Embeddings for Memory/Knowledge always use local `mxbai-embed-large`, because Claude has no embedding model.
- The Python code of the projects is not implemented yet. Each `src/<package>/` is an empty skeleton. Do not write project code in this task.

## Rules

- Detect the OS first (Windows PowerShell or Linux/macOS shell) and use only commands for that OS.
- Never hardcode, print or commit secrets. Keys go only into `.env` files, which are git-ignored. Never ask me to paste a key into the chat; tell me which file and variable to fill in.
- Do not invent CLI flags. Check `--help` before using any flag you are not sure about.
- Do not use `uv tool install crewai`, `pip install`, `python -m venv`, or `crewai install`. The CrewAI CLI is already part of the workspace environment and is run as `uv run crewai ...`. `crewai install` runs `uv sync` in a member folder, which would uninstall packages that other members need.
- Do not run `uv run crewai create` or any sample crew as part of this task (it would make real LLM calls and overwrite folders).
- Installing system software (uv, Node.js, Ollama, Docker) is **ASK**: show the exact command and its source first, and wait for my yes. Do not pipe a downloaded script into a shell without that approval.
- If a command fails: show the exact command and error, explain the likely cause, fix what is safe to fix, and retry once. If it still fails, report it and continue with the remaining steps.

## Steps

### 1. Check prerequisites

Report the version or "missing" for each: `git`, `uv`, `node`/`npx` (optional, only for step 5), `ollama` (optional if I only use Claude), `docker` (optional, only for project 03).

### 2. Install uv if missing (**ASK**)

- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Afterwards make `uv` available in the current shell (open a new terminal, or on Linux `source "$HOME/.local/bin/env"`) and run `uv --version`. Do not install Python separately: uv downloads 3.12 from `.python-version`.

### 3. Create the workspace environment

From the root run `uv sync --locked`. If it fails because `uv.lock` is out of date, run `uv sync` once and tell me that the lock file changed (so I can commit it). Then verify:

```
uv run python --version          # must print 3.12.x
uv run crewai version
uv run python -c "import litellm, anthropic, mcp, fastapi; print('imports ok')"
```

Check that `.venv` was created in the root and that no `.venv` exists inside the member folders.

### 4. Create the `.env` file of each project

For each member folder: if `.env` does not exist, copy `.env.example` to `.env`; if it exists, leave it untouched. Then, in each `.env`, ask me once which provider to use (`claude` or `local`) and set only `LLM_PROVIDER` accordingly. For `claude`, tell me to put `ANTHROPIC_API_KEY` into the three `.env` files myself. Confirm with `git status` that no `.env` is tracked or staged.

### 5. Install the CrewAI coding-agent skills (optional)

If `npx` exists, run once from the repository root: `npx skills add crewaiinc/skills`. Tell me where the skills were written and whether new files appeared in `git status`, so I can decide what to commit. If `npx` is missing or the agent cannot load skills, report the exact issue and continue; use these as the source of truth instead:

- https://docs.crewai.com/llms.txt
- https://docs.crewai.com/en/installation
- https://docs.crewai.com/en/guides/coding-tools/build-with-ai
- https://skills.crewai.com

### 6. Local model setup (only if some project uses `local`, or for embeddings)

If `ollama` is missing, tell me where to get it (https://ollama.com) and skip. Otherwise check `ollama list` and pull only what is missing, each after my OK because of the download size:

```
ollama pull qwen3.5:9b            # ~6.6 GB, local LLM
ollama pull mxbai-embed-large     # ~0.7 GB, embeddings for Memory / Knowledge
```

Ollama's default context (4096 tokens) is too small for CrewAI prompts. Do not edit system settings; instead tell me to start the server with a larger context:

- Windows PowerShell: `$env:OLLAMA_CONTEXT_LENGTH=16384; ollama serve`
- Linux/macOS: `OLLAMA_CONTEXT_LENGTH=16384 ollama serve`

If Ollama is already running as a background service, say that it must be restarted with this variable for it to take effect.

### 7. Smoke test without LLM calls

Run only checks that do not call a model:

```
uv run crewai --help
uv run python -c "from crewai import Agent, Task, Crew, Process, Flow, LLM; print('crewai api ok')"
```

If `ollama` is running, additionally check `http://localhost:11434/api/tags` lists the pulled models.

### 8. Final report

Print a short table: step, status (done / already done / skipped / failed), and what I still have to do by hand (API keys, starting Ollama with the larger context, committing `uv.lock` or skill files). Do not commit anything.

## Optional phase: scaffold a project (only if I ask for it)

Never run this unprompted. When I ask to start implementing project N:

1. Generate the CrewAI scaffold in a scratch folder **outside** the repository (`uv run crewai create crew <name>` for projects 01 and 03, `uv run crewai create flow <name>` for project 02). Run `uv run crewai create --help` first and do not use `CREWAI_DMN` or other undocumented switches.
2. Inspect the generated files before editing, then merge them into the existing member folder. Keep the member's `pyproject.toml` name, `requires-python = ">=3.12,<3.14"`, the `crewai[litellm,anthropic,tools]` dependency and the extra dependencies already listed, and the existing `src/<package>` folder name. Adopt from the scaffold: `config/*.yaml`, `crew.py`/`main.py`, `[tool.crewai]` and the `[project.scripts]` entry points.
3. After merging, run `uv sync` from the **repository root** (never `crewai install`), then `uv run crewai run` (or `uv run crewai flow kickoff` for project 02) from the member folder.
