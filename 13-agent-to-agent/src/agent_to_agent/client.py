"""The A2A client: a coordinator agent that can hand work to the remote currency desk."""

import argparse
import os
import sys

from crewai import Agent
from crewai.a2a import A2AClientConfig
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from agent_to_agent import llm_factory

DEFAULT_QUESTION = "How many PLN do I get for 250 EUR?"


def build_client_agent(endpoint: str, llm=None) -> Agent:
    return Agent(
        role="Coordinator",
        goal="Answer the user; ask the right specialist when you need data you do not have",
        backstory="You do not know exchange rates. Remote specialists do.",
        llm=llm or llm_factory.make_llm(),
        a2a=A2AClientConfig(
            endpoint=endpoint,  # the server's agent card: name, skills, URL
            timeout=120,
            max_turns=4,  # at most 4 messages back and forth with the remote agent
        ),
    )


def ask(question: str, endpoint: str, llm=None) -> str:
    agent = build_client_agent(endpoint, llm)
    return agent.kickoff(question).raw


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    port = os.getenv("A2A_PORT", "9999")
    parser = argparse.ArgumentParser(
        description="Ask a coordinator that can use a remote A2A agent"
    )
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--endpoint", default=f"http://127.0.0.1:{port}/.well-known/agent-card.json"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    print(f"\nanswer: {ask(args.question, args.endpoint)}")
    # must return None: console scripts do sys.exit(run())
