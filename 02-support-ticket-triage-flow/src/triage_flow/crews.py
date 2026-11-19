"""The crews the flow calls: classifier, sentiment, and one specialist crew per ticket category.

Agent and task text lives in config/*.yaml; this module wires LLMs, MCP tools and Knowledge around it.
Every crew is built fresh per call, so each run gets new LLM objects and a new MCP connection.
"""

import os
from pathlib import Path

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.mcp import MCPServerStdio, create_static_tool_filter

from triage_flow import llm_factory
from triage_flow.models import Classification, Sentiment

CONFIG_DIR = Path(__file__).parent / "config"

# category -> agent/task keys, MCP tools it may call, knowledge files (relative to ./knowledge)
SPECIALISTS = {
    "billing": {
        "agent": "billing_specialist",
        "task": "billing_task",
        "tools": ["get_customer", "search_orders"],
        "knowledge": ["billing_policy.md"],
    },
    "bug": {
        "agent": "bug_specialist",
        "task": "bug_task",
        "tools": ["get_customer", "get_ticket"],
        "knowledge": [],
    },
    "how_to": {
        "agent": "howto_specialist",
        "task": "howto_task",
        "tools": ["get_customer"],
        "knowledge": ["product_docs.md"],
    },
}


def _config(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def _agent(key: str, **kwargs) -> Agent:
    return Agent(
        config=_config("agents.yaml")[key],
        llm=llm_factory.make_llm(),
        verbose=llm_factory.env_bool("VERBOSE", False),
        **kwargs,
    )


def _task(key: str, agent: Agent, **kwargs) -> Task:
    return Task(config=_config("tasks.yaml")[key], agent=agent, **kwargs)


def _crew(agent: Agent, task: Task) -> Crew:
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=llm_factory.env_bool("VERBOSE", False),
    )


def ticket_inputs(state) -> dict:
    """Values for the {placeholders} in tasks.yaml (a crew never reads flow state by itself)."""
    return {
        "ticket_id": state.ticket_id,
        "customer_id": state.customer_id,
        "subject": state.subject,
        "body": state.body,
        "customer_context": state.customer_context or "none",
    }


def classifier_crew() -> Crew:
    agent = _agent("classifier")
    return _crew(agent, _task("classify_task", agent, output_pydantic=Classification))


def sentiment_crew() -> Crew:
    agent = _agent("sentiment_analyst")
    return _crew(agent, _task("sentiment_task", agent, output_pydantic=Sentiment))


def ticket_mcp_server(allowed_tools: list[str]) -> MCPServerStdio:
    """The Python FastMCP server in mcp_server.py, started over stdio, limited to the given tools."""
    return MCPServerStdio(
        command="python",
        args=["-m", "triage_flow.mcp_server"],
        # a stdio server gets only a minimal environment: pass PATH (venv python first) and the data dir
        env={
            "PATH": os.environ.get("PATH", ""),
            "TRIAGE_DATA_DIR": os.getenv("TRIAGE_DATA_DIR", ""),
        },
        tool_filter=create_static_tool_filter(allowed_tool_names=allowed_tools),
        cache_tools_list=True,
    )


def specialist_crew(category: str) -> Crew:
    spec = SPECIALISTS[category]
    kwargs: dict = {}
    if llm_factory.env_bool("USE_MCP", True):
        kwargs["mcps"] = [ticket_mcp_server(spec["tools"])]
    if spec["knowledge"] and llm_factory.env_bool("USE_KNOWLEDGE", True):
        kwargs["knowledge_sources"] = [
            TextFileKnowledgeSource(file_paths=spec["knowledge"])
        ]
        kwargs["embedder"] = llm_factory.embedder_config()
    agent = _agent(spec["agent"], **kwargs)
    return _crew(agent, _task(spec["task"], agent))
