"""CLI: code_review_run (review diff files), code_review_train, code_review_test."""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from code_review import llm_factory
from code_review.crew import reviewers_crew
from code_review.listeners import ReviewLogListener
from code_review.review import review_diff
from code_review.tools.diff_parser import chunk_diff
from code_review.usage_tracker import UsageTracker


def run(argv: list[str] | None = None) -> None:
    """Review one or more local diffs; print each comment and the token usage."""
    parser = argparse.ArgumentParser(
        description="Review diff files with the code review crew"
    )
    parser.add_argument(
        "--diff",
        action="append",
        type=Path,
        required=True,
        help="unified diff file (repeatable)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="title used in the prompts (default: the file name)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="checked-out repo; lets reviewers read files",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ReviewLogListener()
    tracker = (
        UsageTracker()
    )  # counts tokens per crew and agent over all diffs of this run
    for (
        path
    ) in args.diff:  # a batch of PRs: reviewed one after another (one local model)
        result = review_diff(
            path.read_text(encoding="utf-8"), args.title or path.name, args.repo_root
        )
        print(
            f"\n=== {result.title}: {len(result.findings)} finding(s), {result.chunks} chunk(s) ===\n"
        )
        print(result.comment)
    print("\n" + tracker.report())
    # must return None: console scripts do sys.exit(run())


def _sample_inputs() -> dict:
    diff = Path("samples/example.diff").read_text(encoding="utf-8")
    return {"title": "Add user lookup", "diff": chunk_diff(diff, 6000)[0]}


def train(argv: list[str] | None = None) -> None:
    """Interactive training: you give feedback on each reviewer output; saves to a .pkl file."""
    parser = argparse.ArgumentParser(
        description="Train the reviewers with human feedback"
    )
    parser.add_argument("-n", "--iterations", type=int, default=2)
    parser.add_argument("-f", "--filename", default="training.pkl")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    inputs = _sample_inputs()
    reviewers_crew(inputs["diff"]).train(
        n_iterations=args.iterations, filename=args.filename, inputs=inputs
    )


def test(argv: list[str] | None = None) -> None:
    """Score the reviewers on the sample diff with an evaluator model (real LLM calls)."""
    parser = argparse.ArgumentParser(
        description="Evaluate the reviewers (model-graded, 1-10)"
    )
    parser.add_argument("-n", "--iterations", type=int, default=2)
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="evaluator model (default: the configured LLM)",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    inputs = _sample_inputs()
    judge = args.model or llm_factory.make_llm()
    reviewers_crew(inputs["diff"]).test(
        n_iterations=args.iterations, eval_llm=judge, inputs=inputs
    )
