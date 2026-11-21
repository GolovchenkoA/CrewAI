"""One crew, two ways to run it.

hierarchical: a manager agent receives the tasks, decides which worker does each one and delegates
              (Process.hierarchical + manager_agent). The tasks have NO agent assigned.
sequential:   the same tasks with agents assigned by hand, run in list order (for comparison).
"""

from crewai import Agent, Crew, Process, Task

from hierarchical_delegation import llm_factory


def _agent(role: str, goal: str, backstory: str, **kwargs) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm_factory.make_llm(),
        verbose=llm_factory.env_bool("VERBOSE", False),
        **kwargs,
    )


def build_crew(process: str = "hierarchical") -> Crew:
    verbose = llm_factory.env_bool("VERBOSE", False)
    researcher = _agent(
        "Researcher",
        "Find accurate key facts about {topic}.",
        "You collect short, factual notes and never invent details.",
    )
    writer = _agent(
        "Writer",
        "Turn notes into clear, short text.",
        "You write plain two-sentence summaries from the notes you are given.",
    )

    research = Task(
        description="Collect three key facts about {topic}.",
        expected_output="Three short bullet points.",
    )
    summary = Task(
        description="Write a two-sentence summary of {topic} using the facts from the research.",
        expected_output="Exactly two sentences.",
    )

    if process == "sequential":
        research.agent, summary.agent = researcher, writer
        return Crew(
            name="sequential_crew",
            agents=[researcher, writer],
            tasks=[research, summary],
            process=Process.sequential,
            verbose=verbose,
        )

    if process != "hierarchical":
        raise ValueError(
            f"process must be 'hierarchical' or 'sequential', got {process!r}"
        )

    manager = _agent(
        "Project Manager",
        "Get the work done by delegating each task to the right coworker.",
        "You never do the work yourself: you delegate and check the result.",
        allow_delegation=True,  # gives the manager the delegate / ask-coworker tools
    )
    return Crew(
        name="hierarchical_crew",
        agents=[researcher, writer],  # the workers; the manager is NOT in this list
        tasks=[research, summary],  # no agent on the tasks: the manager picks
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=verbose,
    )
