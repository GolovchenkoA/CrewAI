import json
from pathlib import Path

import pytest

from stub_llm import StubLLM, prompt_text
from triage_flow import crews, flow as flow_module, llm_factory

SPECIALIST_ROLES = {
    "billing": "Billing Support Specialist",
    "bug": "Technical Support Engineer",
    "how-to": "Product Documentation Expert",
}
TICKET = {
    "ticket_id": "T-1",
    "customer_id": "C-100",
    "subject": "Charged twice",
    "body": "Two charges of 49 EUR.",
}


def make_stub(category: str, confidence: float) -> StubLLM:
    """A fake model that answers by agent role (found in the system message)."""

    def responder(messages, response_model):
        system = str(messages[0]["content"])
        if "Support Ticket Classifier" in system:
            return {"category": category, "confidence": confidence, "reasoning": "stub"}
        if "Customer Sentiment Analyst" in system:
            return {"sentiment": "negative", "urgency": "high"}
        for cat, role in SPECIALIST_ROLES.items():
            if role in system:
                return f"Final Answer: Draft reply from the {cat} specialist."
        raise AssertionError(f"unexpected agent: {system[:80]}")

    return StubLLM(responder=responder)


def run(
    monkeypatch, category: str, confidence: float, answers: list[str] | None = None
):
    stub = make_stub(category, confidence)
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    flow_module.FEEDBACK.answers = list(answers or [])
    flow = flow_module.build_flow()
    flow.kickoff(inputs=TICKET)
    return flow, stub


@pytest.mark.parametrize("category", ["billing", "bug", "how-to"])
def test_router_picks_the_matching_specialist(monkeypatch, category):
    flow, stub = run(monkeypatch, category, 0.95)

    systems = [str(c["messages"][0]["content"]) for c in stub.calls]
    assert any(SPECIALIST_ROLES[category] in s for s in systems)
    other_roles = [r for c, r in SPECIALIST_ROLES.items() if c != category]
    assert not any(r in s for s in systems for r in other_roles), (
        "a wrong specialist ran"
    )
    assert flow.state.category == category
    assert flow.state.final_reply == f"Draft reply from the {category} specialist."


def test_confident_ticket_skips_the_human_and_writes_files(monkeypatch):
    flow, stub = run(monkeypatch, "billing", 0.9)

    assert flow.state.human_reviewed is False
    out = Path("output/T-1")
    assert (out / "reply.md").read_text(encoding="utf-8") == flow.state.final_reply
    record = json.loads((out / "ticket.json").read_text(encoding="utf-8"))
    assert record["category"] == "billing" and record["urgency"] == "high"
    # the specialist saw the ticket text (crews do not read flow state, inputs must be passed)
    assert any(
        "Charged twice" in prompt_text(c)
        and "Billing Support Specialist" in prompt_text(c)
        for c in stub.calls
    )


def test_low_confidence_pauses_for_a_human_who_edits(monkeypatch):
    flow, _ = run(
        monkeypatch, "billing", 0.4, answers=["Corrected reply from a human."]
    )

    assert flow.state.human_reviewed is True
    assert flow.state.final_reply == "Corrected reply from a human."
    assert (
        Path("output/T-1/reply.md").read_text(encoding="utf-8")
        == "Corrected reply from a human."
    )


def test_low_confidence_empty_answer_approves_the_draft(monkeypatch):
    flow, _ = run(monkeypatch, "bug", 0.4, answers=[""])

    assert flow.state.human_reviewed is True
    assert flow.state.final_reply == "Draft reply from the bug specialist."


def test_threshold_is_configurable(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.3")
    flow, _ = run(monkeypatch, "billing", 0.4)

    assert flow.state.human_reviewed is False


def test_specialist_crew_gets_a_filtered_mcp_server_when_enabled(monkeypatch):
    monkeypatch.setenv("USE_MCP", "true")
    stub = make_stub("billing", 0.9)
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)

    agent = crews.specialist_crew("billing").agents[0]

    assert len(agent.mcps) == 1
    assert agent.mcps[0].args == ["-m", "triage_flow.mcp_server"]
    assert agent.mcps[0].tool_filter is not None


def test_flow_plots_without_opening_a_browser():
    path = Path(flow_module.TriageFlow().plot("triage_flow.html", show=False))

    assert path.exists()
    graph = next(path.parent.glob("*.js")).read_text(encoding="utf-8")
    for label in ("billing", "how_to", "auto_send", "human_review"):
        assert label in graph
