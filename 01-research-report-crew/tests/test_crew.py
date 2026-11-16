import json
from pathlib import Path

from crewai import Process

from research_crew.crew import ResearchCrew
from research_crew.main import build_inputs
from research_crew.models import Analysis
from stub_llm import StubLLM, prompt_text, tool_call

ANALYSIS = {
    "topic": "bees",
    "summary": "Bees pollinate crops. They live in colonies. Colonies make honey.",
    "claims": [
        {
            "statement": "Bees pollinate crops",
            "evidence": "notes say so",
            "source": "sample_note.md",
            "confidence": "high",
        }
    ],
    "open_questions": ["How many species?"],
}

REPORT = """# Bees report

## Executive Summary
Bees pollinate crops and live in colonies [sample_note.md].

## Key Findings
- Bees pollinate crops [sample_note.md]
- Colonies produce honey [https://example.com]

## Conclusion
Bees matter for agriculture and food supply in many regions of the world.

## Sources
- sample_note.md
- https://example.com
"""


def responder(messages, response_model):
    """Answer by agent role (found in the system message), like a tiny fake model."""
    system = str(messages[0]["content"])
    everything = "\n".join(str(m.get("content", "")) for m in messages)
    if "Notes Researcher" in system:
        return "Final Answer: - Bees pollinate crops (source: sample_note.md)"
    if "Web Scout" in system:
        return "Final Answer: - Colonies produce honey (source: https://example.com)"
    if "Research Analyst" in system:
        return ANALYSIS
    if "Technical Writer" in system:
        return REPORT
    if "Report Editor" in system:
        if "Observation:" in everything:
            return "Final Answer: " + REPORT
        return tool_call("Word Count", {"text": REPORT})
    raise AssertionError(f"unexpected agent: {system[:80]}")


def crew_with(llm):
    crew = ResearchCrew().crew()
    for agent in crew.agents:
        agent.llm = llm
    return crew


def test_full_sequential_run():
    llm = StubLLM(responder=responder)
    inputs = build_inputs("bees", urls="https://example.com")
    out = crew_with(llm).kickoff(inputs=inputs)

    assert out.raw.startswith("# Bees report")
    assert len(out.tasks_output) == 5

    analysis = out.tasks_output[2].pydantic
    assert isinstance(analysis, Analysis), "structured output was dropped"
    assert analysis.claims[0].confidence == "high"

    report = Path("output/bees/report.md").read_text(encoding="utf-8")
    assert "## Key Findings" in report
    assert json.loads(Path("output/bees/analysis.json").read_text(encoding="utf-8"))["topic"] == "bees"

    prompts = [prompt_text(c) for c in llm.calls]
    assert any("https://example.com" in p and "Web Scout" in p for p in prompts)  # URLs reach the scout
    assert any("Bees pollinate crops" in p and "Technical Writer" in p for p in prompts)  # context flows on
    assert any("Observation: " in p and "words" in p for p in prompts)  # editor used Word Count


def test_batch_runs_use_their_own_inputs():
    llm = StubLLM(responder=responder)
    crew = crew_with(llm)  # a fresh crew: one that already ran would reuse old inputs
    outputs = crew.kickoff_for_each(inputs=[build_inputs("bees"), build_inputs("ants")])

    assert len(outputs) == 2
    assert Path("output/bees/report.md").exists()
    assert Path("output/ants/report.md").exists()


def test_hierarchical_process_has_manager_and_no_async(monkeypatch):
    monkeypatch.setenv("PROCESS", "hierarchical")
    crew = ResearchCrew().crew()

    assert crew.process == Process.hierarchical
    assert crew.manager_llm is not None
    assert not any(t.async_execution for t in crew.tasks)


def test_sequential_process_runs_research_in_parallel():
    crew = ResearchCrew().crew()

    assert crew.process == Process.sequential
    assert [t.async_execution for t in crew.tasks] == [True, True, False, False, False]
