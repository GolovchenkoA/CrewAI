"""Triage an incident; run an expensive deep dive only when the triage says "high".

triage_task      always runs, returns a structured Triage (output_pydantic)
deep_dive_task   ConditionalTask: runs only if condition(previous TaskOutput) is True
report_task      always runs; sees the outputs of the tasks before it (empty if the deep dive was skipped)
"""

from crewai import Agent, Crew, Process, Task, TaskOutput
from crewai.tasks.conditional_task import ConditionalTask

from conditional_tasks import llm_factory
from conditional_tasks.models import Triage


def needs_deep_dive(output: TaskOutput) -> bool:
    """The condition receives the TaskOutput of the task right before the ConditionalTask."""
    triage = output.pydantic
    if not isinstance(
        triage, Triage
    ):  # no valid structure from the model: investigate to be safe
        return True
    return triage.severity == "high"


def _agent(role: str, goal: str, backstory: str) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm_factory.make_llm(),
        verbose=llm_factory.env_bool("VERBOSE", False),
    )


def build_crew() -> Crew:
    analyst = _agent(
        "Incident Analyst",
        "Rate incidents and report them clearly.",
        "You triage incident reports quickly: high means users are blocked or data is at risk.",
    )
    investigator = _agent(
        "Incident Investigator",
        "Find the most likely root cause of a serious incident.",
        "You dig into serious incidents and name one likely root cause and one next step.",
    )

    triage = Task(
        description="Rate the severity of this incident (low or high) and summarise it in one sentence:\n{incident}",
        expected_output="A severity (low or high) and a one-sentence summary.",
        agent=analyst,
        output_pydantic=Triage,
    )
    deep_dive = ConditionalTask(
        description="Investigate this serious incident. Name the most likely root cause and one next step:\n{incident}",
        expected_output="Two sentences: the likely root cause and the next step.",
        agent=investigator,
        condition=needs_deep_dive,
    )
    report = Task(
        description="Write a short status update (max 3 sentences) for the incident, using the triage and, if present, the investigation.",
        expected_output="A status update of at most three sentences.",
        agent=analyst,
        context=[triage, deep_dive],
    )
    return Crew(
        name="incident_crew",
        agents=[analyst, investigator],
        tasks=[triage, deep_dive, report],
        process=Process.sequential,
        verbose=llm_factory.env_bool("VERBOSE", False),
    )
