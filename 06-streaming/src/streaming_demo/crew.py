"""One agent, one task, built with stream=True so the text can be printed while the model writes it."""

from crewai import Agent, Crew, Process, Task

from streaming_demo import llm_factory


def build_crew(stream: bool = True, llm_stream: bool = False) -> Crew:
    writer = Agent(
        role="Explainer",
        goal="Explain {topic} to a beginner.",
        backstory="You write short, clear explanations in plain language.",
        llm=llm_factory.make_llm(
            stream=llm_stream
        ),  # llm_stream: the model sends tokens as they are made
        verbose=llm_factory.env_bool("VERBOSE", False),
    )
    task = Task(
        description="Explain {topic} in three short paragraphs.",
        expected_output="Three short paragraphs.",
        agent=writer,
    )
    return Crew(
        name="streaming_crew",
        agents=[writer],
        tasks=[task],
        process=Process.sequential,
        stream=stream,  # kickoff() then returns a CrewStreamingOutput instead of a CrewOutput
        verbose=llm_factory.env_bool("VERBOSE", False),
    )
