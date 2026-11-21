"""CLI: checkpoint_run run [--fail] | resume [--path FILE] | list"""

import argparse
import os
import sys

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from flow_checkpoint.flow import latest_checkpoint, resume_flow, run_flow


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Flow checkpoint and resume demo")
    sub = parser.add_subparsers(dest="command", required=True)
    run_cmd = sub.add_parser("run", help="run the flow from the start")
    run_cmd.add_argument("--fail", action="store_true", help="make step 2 fail")
    resume_cmd = sub.add_parser("resume", help="continue from a checkpoint")
    resume_cmd.add_argument("--path", help="checkpoint file (default: the newest one)")
    sub.add_parser("list", help="show the newest checkpoint file")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    location = os.getenv("CHECKPOINT_DIR", ".checkpoints")

    if args.command == "run":
        try:
            print(f"result: {run_flow(location, args.fail)}")
        except RuntimeError as exc:
            print(f"\nrun failed: {exc}")
            print(f"newest checkpoint: {latest_checkpoint(location)}")
            print("fix the problem, then: checkpoint_run resume")
    elif args.command == "resume":
        print(f"result: {resume_flow(location, args.path)}")
    else:
        print(latest_checkpoint(location) or "no checkpoints yet")
    # must return None: console scripts do sys.exit(run())
