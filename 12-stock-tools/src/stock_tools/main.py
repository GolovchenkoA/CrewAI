"""CLI: tools_run [--file PATH] [--url URL]"""

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from crewai.events import crewai_event_bus

from stock_tools.agent import ToolLog, research

DEFAULT_FILE = "samples/release_notes.txt"
DEFAULT_URL = "https://example.com"


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Agent with FileReadTool and ScrapeWebsiteTool"
    )
    parser.add_argument("--file", default=DEFAULT_FILE)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    log = ToolLog()
    answer = research(args.file, args.url)
    crewai_event_bus.flush()  # handlers run on worker threads; wait before reading the log
    print(f"\nanswer:\n{answer}")
    print(f"\ntools called: {', '.join(log.calls) or '(none)'}")
    # must return None: console scripts do sys.exit(run())
