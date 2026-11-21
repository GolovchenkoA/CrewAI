"""CLI: hierarchical_run --topic "..." [--process hierarchical|sequential|both]"""

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from crewai.events import crewai_event_bus

from hierarchical_delegation.crew import build_crew
from hierarchical_delegation.listeners import DelegationLog


def run_once(process: str, topic: str) -> str:
    log = DelegationLog()
    result = build_crew(process).kickoff(inputs={"topic": topic})
    crewai_event_bus.flush()  # listener handlers run on worker threads
    print(f"\n=== {process} ===")
    # in a hierarchical crew every TaskOutput.agent is the manager, so the delegations are the evidence
    if log.entries:
        print("delegations made by the manager:")
        for coworker, text in log.entries:
            print(f"  -> {coworker}: {text[:80]}")
    elif process == "hierarchical":
        print("no delegation happened (the manager did the work itself)")
    else:
        print(
            "no manager in a sequential crew: each task has its agent assigned in code"
        )
    print(f"\nresult:\n{result.raw}")
    return result.raw


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Hierarchical process with a manager agent"
    )
    parser.add_argument("--topic", default="honey bees")
    parser.add_argument(
        "--process",
        choices=["hierarchical", "sequential", "both"],
        default="hierarchical",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    for process in (
        ("hierarchical", "sequential") if args.process == "both" else (args.process,)
    ):
        run_once(process, args.topic)
    # must return None: console scripts do sys.exit(run())
