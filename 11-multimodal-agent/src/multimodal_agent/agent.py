"""An agent that answers questions about an image through a vision tool."""

from crewai import Agent

from multimodal_agent import llm_factory
from multimodal_agent.vision import make_vision_tool


def build_agent(llm=None, vision_llm=None) -> Agent:
    return Agent(
        role="Chart analyst",
        goal="Answer questions about images accurately",
        backstory="You cannot see images yourself; you always use look_at_image first.",
        llm=llm or llm_factory.make_llm(),
        tools=[make_vision_tool(vision_llm or llm_factory.make_llm(vision=True))],
        max_iter=4,
    )


def ask(image_path: str, question: str, llm=None, vision_llm=None) -> str:
    agent = build_agent(llm, vision_llm)
    result = agent.kickoff(
        f"Image file: {image_path}\nQuestion: {question}\n"
        "Use the look_at_image tool, then answer in one or two sentences."
    )
    return result.raw
