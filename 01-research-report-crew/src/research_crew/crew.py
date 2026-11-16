import os

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import DirectoryReadTool, FileReadTool, ScrapeWebsiteTool

from research_crew.guardrails import report_guardrail
from research_crew.llm_factory import env_bool, make_llm
from research_crew.models import Analysis
from research_crew.tools import word_count


def _hierarchical() -> bool:
    return os.getenv("PROCESS", "sequential").strip().lower() == "hierarchical"


@CrewBase
class ResearchCrew:
    """Notes + web research -> analysis -> report -> edit."""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---- agents: every agent gets its own LLM object (per-agent token usage) ----

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],  # type: ignore[index]
            llm=make_llm(),
            tools=[DirectoryReadTool(directory=os.getenv("NOTES_DIR", "notes")), FileReadTool()],
            allow_delegation=env_bool("ALLOW_DELEGATION", True),
            max_iter=8,
            verbose=env_bool("VERBOSE", True),
        )

    @agent
    def web_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["web_scout"],  # type: ignore[index]
            llm=make_llm(),
            tools=[ScrapeWebsiteTool()],
            max_iter=8,
            verbose=env_bool("VERBOSE", True),
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],  # type: ignore[index]
            llm=make_llm(),
            verbose=env_bool("VERBOSE", True),
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],  # type: ignore[index]
            llm=make_llm(),
            verbose=env_bool("VERBOSE", True),
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config["editor"],  # type: ignore[index]
            llm=make_llm(),
            tools=[word_count],
            allow_delegation=env_bool("ALLOW_DELEGATION", True),
            max_iter=8,
            verbose=env_bool("VERBOSE", True),
        )

    # ---- tasks ----
    # The two research tasks run in parallel (async) in the sequential process, each on
    # its own agent. In the hierarchical process the manager schedules them instead.

    @task
    def notes_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["notes_research_task"],  # type: ignore[index]
            async_execution=not _hierarchical(),
        )

    @task
    def web_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["web_research_task"],  # type: ignore[index]
            async_execution=not _hierarchical(),
        )

    @task
    def analysis_task(self) -> Task:
        # output_pydantic must be set in Python, not in tasks.yaml
        return Task(
            config=self.tasks_config["analysis_task"],  # type: ignore[index]
            output_pydantic=Analysis,
        )

    @task
    def writing_task(self) -> Task:
        return Task(config=self.tasks_config["writing_task"])  # type: ignore[index]

    @task
    def editing_task(self) -> Task:
        return Task(
            config=self.tasks_config["editing_task"],  # type: ignore[index]
            guardrail=report_guardrail,
            guardrail_max_retries=3,
        )

    # ---- crew ----

    @crew
    def crew(self) -> Crew:
        extra: dict = {}
        if _hierarchical():
            # MANAGER_LLM_PROVIDER lets a weak local model use Claude as the manager
            extra = {"manager_llm": make_llm(os.getenv("MANAGER_LLM_PROVIDER") or None)}
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical if _hierarchical() else Process.sequential,
            verbose=env_bool("VERBOSE", True),
            **extra,
        )
