"""One agent with two ready-made tools from crewai_tools (no custom tool code)."""

from crewai import Agent
from crewai.events import BaseEventListener, ToolUsageFinishedEvent
from crewai_tools import FileReadTool, ScrapeWebsiteTool

from stock_tools import llm_factory


def default_tools() -> list:
    # Both need no API key. FileReadTool reads a local file; ScrapeWebsiteTool fetches a page over HTTP.
    return [FileReadTool(), ScrapeWebsiteTool()]


def build_agent(llm=None, tools=None) -> Agent:
    return Agent(
        role="Research assistant",
        goal="Answer from the given file and web page, never from memory",
        backstory="You always read the sources with your tools before answering.",
        llm=llm or llm_factory.make_llm(),
        tools=tools if tools is not None else default_tools(),
        max_iter=6,
    )


class ToolLog(BaseEventListener):
    """Which tools did the agent actually call?"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        super().__init__()

    def setup_listeners(self, crewai_event_bus) -> None:
        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool(source, event) -> None:
            self.calls.append(event.tool_name)


def research(file_path: str, url: str, llm=None, tools=None) -> str:
    agent = build_agent(llm, tools)
    result = agent.kickoff(
        f"1. Read the file {file_path} and name the newest version and one change in it.\n"
        f"2. Read the web page {url} and give its main heading.\n"
        "Answer in two short lines, one per source."
    )
    return result.raw
