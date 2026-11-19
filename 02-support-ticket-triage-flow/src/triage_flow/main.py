"""Entry points: triage_flow_kickoff / triage_flow_plot."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from triage_flow.flow import TriageFlow, build_flow

TICKET_FIELDS = ("ticket_id", "customer_id", "subject", "body")


def load_ticket(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: data[k] for k in TICKET_FIELDS}


def kickoff(argv: list[str] | None = None) -> None:
    """Triage tickets: all of data/tickets/*.json, or the files given with --ticket."""
    parser = argparse.ArgumentParser(description="Triage support tickets")
    parser.add_argument(
        "--ticket", action="append", type=Path, help="ticket JSON file (repeatable)"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="approve low-confidence drafts without asking",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.auto:
        import os

        os.environ["HITL_MODE"] = "auto"

    paths = args.ticket or sorted(Path("data/tickets").glob("*.json"))
    if not paths:
        sys.exit(
            "No tickets found (run from the project folder or pass --ticket FILE)."
        )

    for path in paths:
        flow = build_flow()
        flow.kickoff(inputs=load_ticket(path))
        s = flow.state
        review = "human-reviewed" if s.human_reviewed else "auto"
        print(
            f"{s.ticket_id}: {s.category} ({s.confidence:.2f}), {s.sentiment}/{s.urgency}, {review} "
            f"-> output/{s.ticket_id}/reply.md"
        )
    # must return None: console scripts do sys.exit(kickoff())


def plot() -> None:
    print(TriageFlow().plot("triage_flow.html", show=False))
