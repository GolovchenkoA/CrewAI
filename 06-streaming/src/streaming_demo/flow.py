"""A two-step flow, streamed: the chunks of the crew run inside step 1 arrive while the flow is running."""

from crewai.flow import Flow, listen, start
from pydantic import BaseModel

from streaming_demo.crew import build_crew


class State(BaseModel):
    topic: str = "honey bees"
    text: str = ""


class ExplainFlow(Flow[State]):
    @start()
    def explain(self) -> str:
        # the crew itself is not streaming; the LLM is, and the flow's stream=True forwards its chunks
        result = build_crew(stream=False, llm_stream=True).kickoff(
            inputs={"topic": self.state.topic}
        )
        self.state.text = result.raw
        return self.state.text

    @listen(explain)
    def finish(self) -> str:
        return f"[{len(self.state.text.split())} words]"
