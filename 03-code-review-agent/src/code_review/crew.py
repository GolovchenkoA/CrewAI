"""The two crews of a review.

1. reviewers_crew: security + style reviewers run in parallel (async tasks), then the test reviewer.
   Each returns structured findings (output_pydantic). Run once per diff chunk.
2. lead_crew: one agent turns the merged findings into the Markdown comment; a guardrail rejects
   a comment that drops a file:line reference.

Agent and task text lives in config/*.yaml; this module wires LLMs, tools, limits and guardrails.
Crews are built fresh per call, so each run gets new LLM objects (token usage is counted per LLM).
"""

import os
from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task, TaskOutput

from code_review import llm_factory
from code_review.models import Finding, ReviewFindings
from code_review.tools import DiffSummaryTool, RepoFileTool

CONFIG_DIR = Path(__file__).parent / "config"


def _config(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def _agent(key: str, tools: list | None = None) -> Agent:
    return Agent(
        config=_config("agents.yaml")[key],
        llm=llm_factory.make_llm(),
        tools=tools or [],
        verbose=llm_factory.env_bool("VERBOSE", False),
        # retries, rate limit and timeouts
        max_rpm=int(os.getenv("MAX_RPM", "30")),
        max_retry_limit=int(os.getenv("MAX_RETRY_LIMIT", "2")),
        max_execution_time=int(os.getenv("AGENT_TIMEOUT", "900")),
        allow_delegation=False,
    )


def _task(key: str, agent: Agent, **kwargs: Any) -> Task:
    return Task(config=_config("tasks.yaml")[key], agent=agent, **kwargs)


def reviewers_crew(full_diff: str, repo_root: Path | None = None) -> Crew:
    """Three reviewers. `full_diff` is the whole PR (for the changed-files tool), not the chunk."""
    repo_tools = [RepoFileTool(root=repo_root)] if repo_root else []
    security = _agent("security_reviewer", repo_tools)
    style = _agent("style_reviewer", repo_tools)
    tests = _agent("test_reviewer", [DiffSummaryTool(diff=full_diff), *repo_tools])
    return Crew(
        name="reviewers_crew",  # the "team" label in the token usage report
        agents=[security, style, tests],
        tasks=[
            # async tasks run concurrently, each needs its own agent; the crew must end with a sync task
            _task(
                "security_task",
                security,
                async_execution=True,
                output_pydantic=ReviewFindings,
            ),
            _task(
                "style_task",
                style,
                async_execution=True,
                output_pydantic=ReviewFindings,
            ),
            _task("test_task", tests, output_pydantic=ReviewFindings),
        ],
        process=Process.sequential,
        planning=llm_factory.env_bool("PLANNING", False),
        planning_llm=llm_factory.make_llm()
        if llm_factory.env_bool("PLANNING", False)
        else None,
        verbose=llm_factory.env_bool("VERBOSE", False),
    )


def references_every_finding(findings: list[Finding]):
    """Guardrail factory: the comment must contain `file:line` for every finding."""

    def guardrail(output: TaskOutput) -> tuple[bool, Any]:
        missing = [
            f"{f.file}:{f.line}"
            for f in findings
            if f"{f.file}:{f.line}" not in output.raw
        ]
        if missing:
            return (
                False,
                "The comment must mention every finding as `path:line`. Missing: "
                + ", ".join(missing),
            )
        return (True, output.raw)

    return guardrail


def lead_crew(findings: list[Finding]) -> Crew:
    lead = _agent("lead_reviewer")
    task = _task(
        "lead_task",
        lead,
        guardrail=references_every_finding(findings),
        guardrail_max_retries=int(os.getenv("GUARDRAIL_RETRIES", "2")),
    )
    return Crew(
        name="lead_crew",
        agents=[lead],
        tasks=[task],
        process=Process.sequential,
        verbose=llm_factory.env_bool("VERBOSE", False),
    )
