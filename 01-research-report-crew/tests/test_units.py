import pytest
from crewai import TaskOutput

from research_crew.guardrails import report_guardrail
from research_crew.llm_factory import env_bool, make_llm
from research_crew.main import build_inputs, slugify
from research_crew.tools import word_count

GOOD = (
    "# Title\n\n## Executive Summary\nShort text here for the summary part.\n\n"
    "## Key Findings\n- one\n- two\n\n## Conclusion\nDone with the conclusion text.\n\n## Sources\n- a\n"
)


def check(text: str):
    return report_guardrail(TaskOutput(description="d", raw=text, agent="editor"))


def test_guardrail_accepts_complete_report():
    ok, value = check(GOOD)
    assert ok and value.startswith("# Title")


def test_guardrail_strips_code_fence():
    ok, value = check("```markdown\n" + GOOD + "\n```")
    assert ok and not value.startswith("```")


@pytest.mark.parametrize(
    "missing", ["Executive Summary", "Key Findings", "Conclusion", "Sources"]
)
def test_guardrail_rejects_missing_section(missing):
    ok, feedback = check(GOOD.replace(missing, "Other"))
    assert not ok and missing in feedback


def test_guardrail_rejects_short_report(monkeypatch):
    monkeypatch.setenv("MIN_REPORT_WORDS", "500")
    ok, feedback = check(GOOD)
    assert not ok and "at least 500" in feedback


def test_word_count_tool():
    assert word_count.run(text="# H\none two three") == "5 words, 1 headings"


def test_slug_and_inputs():
    assert slugify("LangGraph vs CrewAI!") == "langgraph-vs-crewai"
    inputs = build_inputs("LangGraph vs CrewAI", urls="https://a.b")
    assert inputs["output_dir"] == "output/langgraph-vs-crewai"
    assert inputs["source_urls"] == "https://a.b"


def test_make_llm_switches_provider():
    local = make_llm("local")
    assert "11434" in local.base_url and "qwen" in local.model
    assert make_llm("claude").model.endswith("claude-sonnet-5-5")
    assert make_llm("local") is not make_llm("local")  # one LLM object per agent
    with pytest.raises(ValueError):
        make_llm("gpt")


def test_env_bool(monkeypatch):
    monkeypatch.setenv("X", "False")
    assert env_bool("X", True) is False
    monkeypatch.delenv("X")
    assert env_bool("X", True) is True
