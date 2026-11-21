from conditional_tasks import llm_factory
from conditional_tasks.crew import build_crew, needs_deep_dive
from conditional_tasks.models import Triage
from stub_llm import StubLLM

INCIDENT = "Checkout returns HTTP 500."


def make_stub(severity: str) -> StubLLM:
    def responder(messages, response_model):
        system = str(messages[0]["content"])
        if "Incident Analyst" in system and response_model is Triage:
            return {"severity": severity, "summary": "Checkout is down."}
        if "Incident Investigator" in system:
            return "Final Answer: Root cause: bad deploy. Next step: roll back."
        if "Incident Analyst" in system:
            return "Final Answer: Status update."
        raise AssertionError(f"unexpected agent: {system[:80]}")

    return StubLLM(responder=responder)


def run(monkeypatch, severity: str):
    stub = make_stub(severity)
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    return build_crew().kickoff(inputs={"incident": INCIDENT}), stub


def investigator_calls(stub: StubLLM) -> list:
    return [
        c
        for c in stub.calls
        if "Incident Investigator" in str(c["messages"][0]["content"])
    ]


def test_high_severity_runs_the_deep_dive(monkeypatch):
    result, stub = run(monkeypatch, "high")

    triage, deep_dive, report = result.tasks_output
    assert triage.pydantic.severity == "high"
    assert "roll back" in deep_dive.raw
    assert len(investigator_calls(stub)) == 1
    assert report.raw == "Status update."


def test_low_severity_skips_the_deep_dive(monkeypatch):
    result, stub = run(monkeypatch, "low")

    triage, deep_dive, report = result.tasks_output
    assert triage.pydantic.severity == "low"
    assert deep_dive.raw == ""  # skipped, but still listed in tasks_output
    assert investigator_calls(stub) == []  # the investigator never called the model
    assert report.raw == "Status update."  # the report task still ran


def test_condition_truth_table():
    class Out:
        def __init__(self, pydantic):
            self.pydantic = pydantic

    assert needs_deep_dive(Out(Triage(severity="high", summary="x"))) is True
    assert needs_deep_dive(Out(Triage(severity="low", summary="x"))) is False
    assert (
        needs_deep_dive(Out(None)) is True
    )  # no valid structure: investigate to be safe
