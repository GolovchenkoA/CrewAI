"""Three ways to use CrewAI without a Crew.

1. plain_call        LLM.call(prompt)                          -> text
2. structured_call   LLM.call(messages, response_model=Model)  -> a Model instance
3. agent_with_tool   Agent.kickoff(prompt, response_format=Model) -> LiteAgentOutput (.raw, .pydantic)
"""

from crewai import Agent
from crewai.tools import tool
from pydantic import BaseModel, Field

from standalone_calls import llm_factory


class City(BaseModel):
    name: str
    country: str
    population_millions: float = Field(description="Approximate population in millions")


class WordReport(BaseModel):
    text: str
    word_count: int


@tool("word_counter")
def word_counter(text: str) -> int:
    """Count the words in a piece of text."""
    return len(text.split())


def plain_call(prompt: str = "In one sentence: what is a hash map?") -> str:
    return llm_factory.make_llm().call(prompt)


def structured_call(question: str = "Tell me about Warsaw.") -> City:
    messages = [
        {"role": "system", "content": "Answer with the requested fields only."},
        {"role": "user", "content": question},
    ]
    return llm_factory.make_llm().call(messages, response_model=City)


def agent_with_tool(text: str = "CrewAI agents can run without a crew") -> "object":
    agent = Agent(
        role="Text Analyst",
        goal="Report on texts, using tools for exact numbers.",
        backstory="You never guess counts: you call the word_counter tool.",
        llm=llm_factory.make_llm(),
        tools=[word_counter],
        verbose=llm_factory.env_bool("VERBOSE", False),
    )
    # no Task, no Crew: one prompt in, a LiteAgentOutput out
    return agent.kickoff(
        f"Count the words in this text and report them: {text!r}",
        response_format=WordReport,
    )
