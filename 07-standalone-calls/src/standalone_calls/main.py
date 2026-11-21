"""CLI: standalone_run --example llm|structured|agent|all"""

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from standalone_calls import examples


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Use CrewAI without a Crew")
    parser.add_argument(
        "--example", choices=["llm", "structured", "agent", "all"], default="all"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    pick = args.example

    if pick in ("llm", "all"):
        print("== LLM.call ==")
        print(examples.plain_call())
    if pick in ("structured", "all"):
        print("\n== LLM.call(response_model=City) ==")
        city = examples.structured_call()
        print(repr(city))
    if pick in ("agent", "all"):
        print("\n== Agent.kickoff(response_format=WordReport) with a tool ==")
        out = examples.agent_with_tool()
        print(f"raw:      {out.raw}")
        print(f"pydantic: {out.pydantic!r}")
    # must return None: console scripts do sys.exit(run())
