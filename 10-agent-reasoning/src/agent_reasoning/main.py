"""CLI: reasoning_run --mode plain|reasoning|both [--effort low|medium|high] [--task "..."]"""

import argparse
import sys
import time

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from crewai.events import crewai_event_bus

from agent_reasoning.agent import TASK, build_crew
from agent_reasoning.listeners import ReasoningLog


def run_once(reasoning: bool, effort: str, task: str) -> None:
    log = ReasoningLog()
    started = time.monotonic()
    result = build_crew(reasoning, effort, task).kickoff()
    crewai_event_bus.flush()  # handlers run on worker threads; wait before reading the log
    seconds = time.monotonic() - started

    label = f"reasoning (effort={effort})" if reasoning else "plain (no planning)"
    print(f"\n===== {label} =====")
    if reasoning:
        for summary, ready in log.plans:
            print(f"PLAN (ready={ready}): {summary}")
        print("PLANNED STEPS:", *log.planned_steps or ["(none)"], sep="\n  ")
        print("EXECUTED AS STEPS:", *log.executed_steps or ["(none)"], sep="\n  ")
        for error in log.errors:
            print(f"PLANNING FAILED: {error}")
    print(f"\nANSWER:\n{result.raw}")
    print(
        f"\n[{seconds:.0f}s, {log.llm_calls} LLM calls, "
        f"{result.token_usage.total_tokens} tokens]"
    )


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Agent planning (reasoning) demo")
    parser.add_argument(
        "--mode", choices=["plain", "reasoning", "both"], default="both"
    )
    parser.add_argument("--effort", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--task", default=TASK)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.mode in ("plain", "both"):
        run_once(False, args.effort, args.task)
    if args.mode in ("reasoning", "both"):
        run_once(True, args.effort, args.task)
    # must return None: console scripts do sys.exit(run())
