# CrewAI Learning Projects

Three hands-on projects that together cover the main aspects of [CrewAI](https://docs.crewai.com). Each one has its own virtual environment, `requirements.txt`, `.env.example` and README with setup and run steps for Windows and Linux.

All projects use Python 3.12 (3.13 also works; CrewAI 1.15.x does not support 3.14) and can switch between Claude and a local Ollama model via LiteLLM with `LLM_PROVIDER=claude|local`.

| Project | What it does | Main CrewAI topics |
|---|---|---|
| [01-research-report-crew](01-research-report-crew/README.md) | Four agents (researcher, analyst, writer, editor) turn a topic into a Markdown report. | Agents, tasks, crews, YAML config, sequential and hierarchical process, tools, structured output, guardrails, async tasks |
| [02-support-ticket-triage-flow](02-support-ticket-triage-flow/README.md) | An event-driven flow classifies support tickets, routes them to specialist crews and escalates to a human when confidence is low. | Flows, routers, typed state, MCP tools, Knowledge (RAG), Memory, human-in-the-loop |
| [03-code-review-agent](03-code-review-agent/README.md) | A webhook service where security, style and test reviewers review pull requests and post a summary. | Planning, train and test, event listeners, observability, cost tracking, batch runs, Docker deployment |

Suggested order: 01 teaches the vocabulary, 02 the architecture, 03 the operations.

## Status

Only documentation and setup files exist so far; the Python code is not implemented yet.

## Repository layout

```
.
├── 01-research-report-crew/
├── 02-support-ticket-triage-flow/
├── 03-code-review-agent/
├── .gitignore
└── README.md
```

Each project keeps its own `.venv/` and `.env` (both git-ignored). Copy `.env.example` to `.env` and fill in your keys.
