"""One agent, one multi-step task, with or without agent-level planning (reasoning)."""

from crewai import Agent, Crew, Task
from crewai.agent.planning_config import PlanningConfig

from agent_reasoning import llm_factory

TASK = (
    "Plan a 2-day budget trip to Krakow: pick 3 sights per day, estimate the cost of each day, "
    "then finish with a one-line packing tip."
)


def build_crew(
    reasoning: bool, effort: str = "low", task: str = TASK, llm=None
) -> Crew:
    """`reasoning=True` gives the agent a PlanningConfig: it plans, then runs each plan step."""
    agent = Agent(
        role="Trip planner",
        goal="Make practical, budget-aware travel plans",
        backstory="A careful planner who checks every part of the request.",
        llm=llm or llm_factory.make_llm(),
        # Agent-level planning. `reasoning=True` / `max_reasoning_attempts` are deprecated aliases.
        planning_config=(
            PlanningConfig(
                reasoning_effort=effort,  # low | medium | high: how much the agent reviews after each step
                max_attempts=2,  # plan refinements; None keeps refining until the model says "ready"
                max_steps=5,  # cap on planned steps
                step_timeout=180,  # seconds per plan step
            )
            if reasoning
            else None
        ),
    )
    work = Task(
        description=task, expected_output="The plan, as a short list.", agent=agent
    )
    return Crew(agents=[agent], tasks=[work])
