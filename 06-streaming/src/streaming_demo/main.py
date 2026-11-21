"""CLI: streaming_run --mode crew|flow|compare --topic "..." """

import argparse
import sys
import time

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from streaming_demo.crew import build_crew
from streaming_demo.flow import ExplainFlow


def print_stream(streaming) -> tuple[int, float | None]:
    """Print chunks as they arrive; return (number of chunks, seconds until the first chunk)."""
    started = time.monotonic()
    first: float | None = None
    count = 0
    for chunk in streaming:  # blocks until the next chunk; ends when the run is done
        if first is None:
            first = time.monotonic() - started
        count += 1
        if chunk.content:
            print(chunk.content, end="", flush=True)
        elif hasattr(
            chunk, "type"
        ):  # a flow stream also carries events (a StreamFrame): show them as markers
            print(f"\n· {chunk.type}", flush=True)
    print()
    return count, first


def run_crew(topic: str) -> str:
    streaming = build_crew(stream=True).kickoff(inputs={"topic": topic})
    count, first = print_stream(streaming)
    print(
        f"\n[{count} chunks, first after {first or 0:.1f}s, {len(streaming.result.raw.split())} words in the result]"
    )
    return streaming.result.raw


def run_flow(topic: str) -> str:
    flow = ExplainFlow(stream=True)
    streaming = flow.kickoff(inputs={"topic": topic})
    count, first = print_stream(streaming)
    print(
        f"\n[{count} chunks, first after {first or 0:.1f}s, flow result: {streaming.result}]"
    )
    return str(streaming.result)


def run_compare(topic: str) -> None:
    """The same crew without streaming: nothing is printed until the whole answer is ready."""
    started = time.monotonic()
    result = build_crew(stream=False).kickoff(inputs={"topic": topic})
    print(result.raw)
    print(
        f"\n[no streaming: the first output appeared after {time.monotonic() - started:.1f}s]"
    )


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Stream crew and flow output")
    parser.add_argument("--mode", choices=["crew", "flow", "compare"], default="crew")
    parser.add_argument("--topic", default="honey bees")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    {"crew": run_crew, "flow": run_flow, "compare": run_compare}[args.mode](args.topic)
    # must return None: console scripts do sys.exit(run())
