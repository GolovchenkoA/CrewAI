from crewai import Agent, Crew, Task
from crewai.events import crewai_event_bus

from stub_llm import StubLLM
from triage_flow.usage_tracker import NO_CREW, UsageTracker


def make_crew(name: str, role: str, llm: StubLLM, tasks: int = 1) -> Crew:
    agent = Agent(role=role, goal="Answer", backstory="Brief.", llm=llm)
    return Crew(
        name=name,
        agents=[agent],
        tasks=[Task(description=f"Task {i}", expected_output="Text", agent=agent) for i in range(tasks)],
    )


def test_tokens_are_split_per_crew_and_agent():
    with crewai_event_bus.scoped_handlers():
        tracker = UsageTracker()
        classifier_llm = StubLLM(responses=["billing"], prompt_tokens_per_call=100, completion_tokens_per_call=10)
        billing_llm = StubLLM(responses=["a", "b"], prompt_tokens_per_call=200, completion_tokens_per_call=20)

        make_crew("classifier_crew", "Classifier", classifier_llm).kickoff()
        make_crew("billing_crew", "Billing Specialist", billing_llm, tasks=2).kickoff()

        crews = tracker.by_crew()
        assert crews["classifier_crew"].total_tokens == 110
        assert crews["classifier_crew"].requests == 1
        assert crews["billing_crew"].total_tokens == 2 * 220
        assert crews["billing_crew"].requests == 2

        agents = tracker.snapshot()
        assert agents[("classifier_crew", "Classifier")].prompt_tokens == 100
        assert agents[("billing_crew", "Billing Specialist")].completion_tokens == 40

        assert tracker.total().total_tokens == 110 + 440
        report = tracker.report()
        assert "classifier_crew" in report and "Billing Specialist" in report and "TOTAL" in report


def test_shared_llm_is_not_double_counted():
    """One LLM object used by two agents: events still count every call exactly once."""
    with crewai_event_bus.scoped_handlers():
        tracker = UsageTracker()
        shared = StubLLM(responses=["x", "y"], prompt_tokens_per_call=10, completion_tokens_per_call=5)
        a = Agent(role="A", goal="g", backstory="b", llm=shared)
        b = Agent(role="B", goal="g", backstory="b", llm=shared)
        crew = Crew(
            name="pair_crew",
            agents=[a, b],
            tasks=[
                Task(description="one", expected_output="t", agent=a),
                Task(description="two", expected_output="t", agent=b),
            ],
        )
        crew.kickoff()

        assert tracker.total().requests == 2
        assert tracker.total().total_tokens == 30


def test_calls_outside_a_crew_are_labelled():
    with crewai_event_bus.scoped_handlers():
        tracker = UsageTracker()
        llm = StubLLM(responses=["hi"], prompt_tokens_per_call=7, completion_tokens_per_call=3)
        agent = Agent(role="Solo", goal="g", backstory="b", llm=llm)
        agent.kickoff("Say hi")  # standalone agent, no crew

        assert tracker.by_crew()[NO_CREW].total_tokens == 10


def test_empty_report():
    with crewai_event_bus.scoped_handlers():
        assert "no LLM calls" in UsageTracker().report()
