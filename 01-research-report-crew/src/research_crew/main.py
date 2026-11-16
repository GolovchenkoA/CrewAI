#!/usr/bin/env python
"""Entry points: run (single topic or batch), train, replay, test."""
import argparse
import os
import re
import sys
import warnings
from datetime import datetime

from dotenv import find_dotenv, load_dotenv

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

load_dotenv(find_dotenv(usecwd=True))

from research_crew.crew import ResearchCrew  # noqa: E402  (after load_dotenv)

DEFAULT_TOPIC = "LangGraph vs CrewAI"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "topic"


def build_inputs(topic: str, urls: str | None = None) -> dict:
    """Template variables for config/*.yaml; output goes to output/<topic-slug>/."""
    return {
        "topic": topic,
        "current_year": str(datetime.now().year),
        "source_urls": urls or os.getenv("SOURCE_URLS", ""),
        "notes_dir": os.getenv("NOTES_DIR", "notes"),
        "output_dir": f"output/{slugify(topic)}",
    }


def run() -> None:
    """Run the crew for one topic (--topic) or several (--topics "a;b;c")."""
    parser = argparse.ArgumentParser(description="Research & report crew")
    parser.add_argument("--topic", help="Single topic (default: TOPIC from .env)")
    parser.add_argument("--topics", help="Several topics separated by ';' (batch run)")
    parser.add_argument("--urls", help="Comma-separated pages to scrape (default: SOURCE_URLS)")
    args = parser.parse_args()

    if args.topics:
        topics = [t.strip() for t in args.topics.split(";") if t.strip()]
        inputs = [build_inputs(t, args.urls) for t in topics]
        # kickoff_for_each on a fresh crew: a crew that already ran would reuse old inputs
        ResearchCrew().crew().kickoff_for_each(inputs=inputs)
        for item in inputs:
            print(f"Report: {item['output_dir']}/report.md")
        return

    topic = args.topic or os.getenv("TOPIC") or DEFAULT_TOPIC
    inputs_single = build_inputs(topic, args.urls)
    result = ResearchCrew().crew().kickoff(inputs=inputs_single)
    usage = result.token_usage
    print(f"\nReport:   {inputs_single['output_dir']}/report.md")
    print(f"Analysis: {inputs_single['output_dir']}/analysis.json")
    print(f"Tokens:   {usage.total_tokens} total, {usage.successful_requests} requests")
    # do not return the CrewOutput: the console script would exit with status 1


def _default_inputs() -> dict:
    return build_inputs(os.getenv("TOPIC") or DEFAULT_TOPIC)


def train() -> None:
    """Usage: research_crew_train <iterations> <file.pkl>"""
    try:
        ResearchCrew().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=_default_inputs()
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay() -> None:
    """Usage: research_crew_replay <task_id>"""
    try:
        ResearchCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test() -> None:
    """Usage: research_crew_test <iterations> <eval_llm>"""
    try:
        ResearchCrew().crew().test(
            n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=_default_inputs()
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    run()
