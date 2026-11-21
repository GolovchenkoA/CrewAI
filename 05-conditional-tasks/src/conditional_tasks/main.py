"""CLI: conditional_run --sample high|low   or   conditional_run --incident "text" """

import argparse
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from conditional_tasks.crew import build_crew

SAMPLES = {
    "high": "The payment API has returned HTTP 500 for every request since 09:40. Customers cannot check out.",
    "low": "The footer of the help page shows last year's copyright date.",
}


def run_once(incident: str) -> str:
    result = build_crew().kickoff(inputs={"incident": incident})
    triage, deep_dive, report = result.tasks_output
    print(f"triage:    {triage.pydantic.severity if triage.pydantic else '?'}")
    # a skipped ConditionalTask still appears in tasks_output, with an empty raw
    print(f"deep dive: {'ran' if deep_dive.raw else 'skipped'}")
    if deep_dive.raw:
        print(f"  {deep_dive.raw}")
    print(f"\nstatus update:\n{report.raw}")
    return report.raw


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Conditional task: deep dive only for high severity"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sample", choices=sorted(SAMPLES), default="high")
    group.add_argument("--incident", help="your own incident text")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    run_once(args.incident or SAMPLES[args.sample])
    # must return None: console scripts do sys.exit(run())
