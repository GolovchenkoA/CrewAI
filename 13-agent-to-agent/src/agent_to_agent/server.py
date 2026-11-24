"""The A2A server: one CrewAI agent (a currency desk) exposed over the agent-to-agent protocol."""

import argparse
import os
import sys

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from crewai import Agent
from crewai.a2a import A2AServerConfig
from crewai.a2a.utils.task import cancel, execute
from crewai.tools import tool
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from agent_to_agent import llm_factory

HOST = "127.0.0.1"
PORT = 9999

# Made-up desk rates: a client cannot know them, so a correct answer proves the server was asked.
RATES = {("EUR", "PLN"): 4.27, ("USD", "PLN"): 3.91, ("EUR", "USD"): 1.09}


@tool("exchange_rate")
def exchange_rate(from_currency: str, to_currency: str) -> str:
    """Return the desk exchange rate: how many units of to_currency one unit of from_currency buys."""
    pair = (from_currency.upper(), to_currency.upper())
    if pair in RATES:
        return f"1 {pair[0]} = {RATES[pair]} {pair[1]}"
    return f"no rate for {pair[0]}/{pair[1]}; known pairs: {sorted(RATES)}"


def build_server_agent(llm=None, url: str | None = None) -> Agent:
    return Agent(
        role="Currency desk",
        goal="Convert amounts between currencies with the desk rates",
        backstory="You only use the exchange_rate tool for rates and never guess them.",
        llm=llm or llm_factory.make_llm(),
        tools=[exchange_rate],
        # This is what makes the agent an A2A server: it can now describe itself in an agent card.
        a2a=A2AServerConfig(url=url or f"http://{HOST}:{PORT}"),
    )


class CrewAIExecutor(AgentExecutor):
    """The a2a-sdk calls this for every incoming task; crewai runs the agent."""

    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        await execute(self.agent, context, event_queue)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await cancel(context, event_queue)


def build_app(agent: Agent, url: str):
    """The ASGI app: serves /.well-known/agent-card.json and the JSON-RPC endpoint."""
    handler = DefaultRequestHandler(
        agent_executor=CrewAIExecutor(agent), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(
        agent_card=agent.to_agent_card(url), http_handler=handler
    ).build()


def run(argv: list[str] | None = None) -> None:
    # CrewAI prints emoji in its console panels; the default Windows console encoding cannot show them.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="A2A server: a currency desk agent")
    parser.add_argument("--port", type=int, default=int(os.getenv("A2A_PORT", PORT)))
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    url = f"http://{HOST}:{args.port}"
    print(f"agent card: {url}/.well-known/agent-card.json")
    uvicorn.run(build_app(build_server_agent(url=url), url), host=HOST, port=args.port)
    # must return None: console scripts do sys.exit(run())
