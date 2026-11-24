"""CLI: multimodal_run [--image PATH] [--question "..."]"""

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from multimodal_agent.agent import ask

DEFAULT_IMAGE = "samples/sales_chart.png"
DEFAULT_QUESTION = "Which quarter has the highest value, and what is it?"


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Ask an agent about an image")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    print(f"\nanswer: {ask(args.image, args.question)}")
    # must return None: console scripts do sys.exit(run())
