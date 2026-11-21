from agent_reasoning.agent import TASK, build_crew
from agent_reasoning.listeners import ReasoningLog
from crewai.events import crewai_event_bus
from stub_llm import StubLLM, prompt_text

READY = "1. Pick sights\n2. Estimate costs\nREADY: I am ready to execute the task."
ANSWER = "Final Answer: Day 1: Wawel. Day 2: Salt mine."


def run(reasoning: bool, stub: StubLLM) -> tuple[str, ReasoningLog]:
    log = ReasoningLog()
    result = build_crew(reasoning, task=TASK, llm=stub).kickoff()
    crewai_event_bus.flush()
    return result.raw, log


def test_plain_agent_makes_one_call_and_no_plan():
    stub = StubLLM(responses=[ANSWER])

    raw, log = run(False, stub)

    assert raw == "Day 1: Wawel. Day 2: Salt mine."
    assert len(stub.calls) == 1
    assert log.plans == []


def test_reasoning_agent_plans_first_then_answers():
    stub = StubLLM(responses=[READY, ANSWER])

    raw, log = run(True, stub)

    assert raw == "Day 1: Wawel. Day 2: Salt mine."
    assert len(stub.calls) == 2  # one planning call, one answer call
    assert "Krakow" in prompt_text(stub.calls[0])  # the plan is made from the task text
    assert [ready for _, ready in log.plans] == [True]
    assert log.errors == []


def test_planning_config_exists_only_when_reasoning_is_on():
    assert build_crew(False, llm=StubLLM()).agents[0].planning_config is None
    config = build_crew(True, "medium", llm=StubLLM()).agents[0].planning_config
    assert config.reasoning_effort == "medium"
    assert (
        config.max_attempts is not None
    )  # bounded: small models may never say "ready"


def test_not_ready_plan_is_refined_at_most_max_attempts_times():
    stub = StubLLM(responses=["NOT READY", "NOT READY", "NOT READY", ANSWER])

    run(True, stub)

    # initial plan + one refinement (max_attempts=2), then the answer
    assert len(stub.calls) == 3
