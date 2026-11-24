# 12 - Stock tools from `crewai_tools`

## 1. What the project does

One agent with **two ready-made tools** and no custom tool code:

| Tool | What it does | Key needed |
|---|---|---|
| `FileReadTool` | reads a local file | no |
| `ScrapeWebsiteTool` | fetches a web page and returns its text | no |

The task: read `samples/release_notes.txt` (a made-up changelog) and the page `https://example.com`, then answer from those two sources. The script prints the answer and **which tools the agent actually called**.

```
answer:
2.3.0: Added --dry-run flag that lists what would be moved
Example Domain

tools called: read_a_files_content, read_website_content
```

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| Ready-made tools: `from crewai_tools import FileReadTool, ScrapeWebsiteTool` | `agent.py` |
| Giving tools to an agent: `Agent(tools=[...])` | `agent.py` |
| Logging tool calls with an event listener (`ToolUsageFinishedEvent`) | `agent.py` (`ToolLog`) |
| Offline tests: the real file tool runs, the web call is replaced | `tests/test_tools.py` |

### Which stock tools need keys or setup

| Group | Examples | Key / setup |
|---|---|---|
| Local files | `FileReadTool`, `FileWriterTool`, `DirectoryReadTool` | none |
| Plain web scraping | `ScrapeWebsiteTool`, `ScrapeElementFromWebsiteTool` | none (`beautifulsoup4`) |
| Web search | `SerperDevTool` (`SERPER_API_KEY`), `BraveWebSearchTool` (`BRAVE_API_KEY`), `TavilySearchTool` (`TAVILY_API_KEY`), `EXASearchTool` (`EXA_API_KEY`) | API key, and for some an extra: `crewai-tools[tavily-python]`, `[exa-py]` |
| Hosted scraping | `FirecrawlScrapeWebsiteTool` (`FIRECRAWL_API_KEY`), `SpiderTool` | API key and extra |
| RAG over a file (`TXTSearchTool`, `PDFSearchTool`, `CSVSearchTool`, ...) | search inside a document | they build an **embedder when constructed**; the default is OpenAI, so configure a local one (for example Ollama `mxbai-embed-large`) or they need `OPENAI_API_KEY` |

Things worth knowing (crewai-tools 1.15.44):

- **`FileReadTool` only reads below its `base_dir`** (default: the current directory). A path outside returns `Error: Invalid file path ... outside the allowed directory` as the tool result. The agent sees that text; it does not crash. Pass `FileReadTool(base_dir=...)` to widen it on purpose.
- **Tool names the model sees are snake_case**: `Read a file's content` becomes `read_a_files_content`, `Read website content` becomes `read_website_content`. Use these in listeners and logs.
- **Some tools need an extra before they construct** and may open an interactive "install the package?" prompt that blocks scripts. Install the extra first.
- `ScrapeWebsiteTool` goes through crewai-tools' safe-request helper, so it refuses private addresses (no scraping of `localhost`). That is why the tests replace the web call instead of serving a local page.
- A small model uses two simple tools well (`qwen3:4b` was enough here). Many tools on one agent make small models pick wrongly; give each agent only what its task needs.
- Prefer an official MCP server over a native tool when one exists for the service.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 12-stock-tools
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo). The web page needs internet access.

Run, from `12-stock-tools/`:

```bash
uv run tools_run
uv run tools_run --file samples/release_notes.txt --url https://example.com
```

The file must be below the directory you run from.

Tests (offline, no model and no network), from the repository root:

```bash
uv run --package stock-tools pytest 12-stock-tools/tests
```
