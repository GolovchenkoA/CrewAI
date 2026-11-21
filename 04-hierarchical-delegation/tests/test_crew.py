import pytest
from hierarchical_delegation import crew as crew_module
from hierarchical_delegation import llm_factory
from hierarchical_delegation.listeners import DelegationLog
from stub_llm import StubLLM, prompt_text, tool_call

DELEGATE = "Delegate work to coworker"
FACTS = "Final Answer: - fact 1\n- fact 2\n- fact 3"
SUMMARY = "Final Answer: Bees are insects. They make honey."


def stub_for_hierarchy() -> StubLLM:
    """Answers by agent role: the manager delegates twice, the workers answer."""
    manager_calls = {"n": 0}

    def responder(messages, response_model):
        system = str(messages[0]["content"])
        if "Project Manager" in system:
            manager_calls["n"] += 1
            n = manager_calls["n"]
            if n == 1:
                return tool_call(
                    DELEGATE,
                    {
                        "task": "Collect three key facts about bees",
                        "context": "topic: bees",
                        "coworker": "Researcher",
                    },
                )
            if n == 2:
                return FACTS
            if n == 3:
                return tool_call(
                    DELEGATE,
                    {
                        "task": "Write a two-sentence summary",
                        "context": "- fact 1",
                        "coworker": "Writer",
                    },
                )
            return SUMMARY
        if "Researcher" in system:
            return FACTS
        if "Writer" in system:
            return SUMMARY
        raise AssertionError(f"unexpected agent: {system[:80]}")

    return StubLLM(responder=responder)


def test_hierarchical_crew_shape(monkeypatch):
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub_for_hierarchy())

    crew = crew_module.build_crew("hierarchical")

    assert crew.process.value == "hierarchical"
    assert [a.role for a in crew.agents] == ["Researcher", "Writer"]
    assert (
        crew.manager_agent.role == "Project Manager"
        and crew.manager_agent.allow_delegation
    )
    assert all(t.agent is None for t in crew.tasks)  # the manager decides, not the code


def test_manager_delegates_to_both_workers(monkeypatch):
    stub = stub_for_hierarchy()
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    from crewai.events import crewai_event_bus

    with crewai_event_bus.scoped_handlers():
        log = DelegationLog()
        result = crew_module.build_crew("hierarchical").kickoff(
            inputs={"topic": "bees"}
        )
        crewai_event_bus.flush()

    assert [c for c, _ in log.entries] == ["Researcher", "Writer"]
    assert "Bees are insects" in result.raw
    systems = " ".join(str(c["messages"][0]["content"]) for c in stub.calls)
    assert "Researcher" in systems and "Writer" in systems


def test_sequential_crew_assigns_agents_by_hand(monkeypatch):
    stub = StubLLM(responder=lambda m, r: "Final Answer: ok")
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)

    crew = crew_module.build_crew("sequential")
    result = crew.kickoff(inputs={"topic": "bees"})

    assert [t.agent.role for t in crew.tasks] == ["Researcher", "Writer"]
    assert result.raw == "ok" and len(stub.calls) == 2
    assert "bees" in prompt_text(stub.calls[0])


def test_unknown_process_is_rejected(monkeypatch):
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub_for_hierarchy())
    with pytest.raises(ValueError):
        crew_module.build_crew("consensual")
