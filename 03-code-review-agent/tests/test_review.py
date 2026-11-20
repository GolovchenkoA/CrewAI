import json
from pathlib import Path

from code_review import crew as crew_module
from code_review import llm_factory, review
from code_review.listeners import ReviewLogListener
from code_review.models import Finding
from code_review.tools import DiffSummaryTool, RepoFileTool
from stub_llm import StubLLM, prompt_text

DIFF = (Path(__file__).parents[1] / "samples" / "example.diff").read_text(
    encoding="utf-8"
)

SECURITY = {
    "file": "app/users.py",
    "line": 13,
    "severity": "critical",
    "message": "SQL injection",
    "suggestion": "bind parameters",
}
STYLE = {
    "file": "app/users.py",
    "line": 22,
    "severity": "low",
    "message": "unclear name d()",
    "suggestion": "rename",
}
TESTS = {
    "file": "app/users.py",
    "line": 11,
    "severity": "medium",
    "message": "find_user has no test",
    "suggestion": "add one",
}
INVENTED = {
    "file": "nope.py",
    "line": 1,
    "severity": "high",
    "message": "not in the diff",
    "suggestion": "",
}


def make_stub(lead_answers: list[str] | None = None) -> StubLLM:
    """Answers by agent role. `lead_answers` are consumed one per lead-reviewer call."""
    lead_answers = list(lead_answers or [])

    def responder(messages, response_model):
        system = str(messages[0]["content"])
        if "Application Security Reviewer" in system:
            findings = [SECURITY, INVENTED]
        elif "Code Style Reviewer" in system:
            findings = [STYLE, SECURITY]  # SECURITY again: a duplicate to be merged
        elif "Test Coverage Reviewer" in system or response_model is not None:
            findings = [
                TESTS
            ]  # the test reviewer has a tool, so its JSON is converted in a second call
        elif "Lead Reviewer" in system:
            return "Final Answer: " + lead_answers.pop(0)
        else:
            raise AssertionError(f"unexpected agent: {system[:80]}")
        if response_model is not None:
            return {"findings": findings}
        return "Final Answer: " + json.dumps({"findings": findings})

    return StubLLM(responder=responder)


FULL_COMMENT = "Summary.\n- **critical** `app/users.py:13` SQL injection\n- `app/users.py:11` no test\n- `app/users.py:22` name"


def run_review(monkeypatch, stub: StubLLM):
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    return review.review_diff(DIFF, "Add user lookup")


def test_merge_dedupes_drops_unknown_files_and_sorts():
    f = [Finding(**x) for x in (STYLE, SECURITY, SECURITY, INVENTED, TESTS)]

    merged = review.merge_findings([f[:2], f[2:]], {"app/users.py"})

    assert [x.severity for x in merged] == ["critical", "medium", "low"]
    assert all(x.file == "app/users.py" for x in merged)


def test_pipeline_runs_three_reviewers_then_the_lead(monkeypatch):
    stub = make_stub([FULL_COMMENT])

    result = run_review(monkeypatch, stub)

    assert result.chunks == 1
    assert [f.severity for f in result.findings] == ["critical", "medium", "low"]
    assert result.comment == FULL_COMMENT
    systems = " ".join(str(c["messages"][0]["content"]) for c in stub.calls)
    for role in (
        "Application Security",
        "Code Style",
        "Test Coverage",
        "Lead Reviewer",
    ):
        assert role in systems
    # reviewers saw numbered diff lines, the lead saw the merged findings
    assert any("  11 +def find_user" in prompt_text(c) for c in stub.calls)
    lead = next(
        c for c in stub.calls if "Lead Reviewer" in str(c["messages"][0]["content"])
    )
    assert "SQL injection" in prompt_text(lead) and "nope.py" not in prompt_text(lead)


def test_guardrail_retries_when_a_reference_is_missing(monkeypatch):
    stub = make_stub(["Summary only, no references.", FULL_COMMENT])

    result = run_review(monkeypatch, stub)

    assert result.comment == FULL_COMMENT
    leads = [
        c for c in stub.calls if "Lead Reviewer" in str(c["messages"][0]["content"])
    ]
    assert len(leads) == 2
    assert "app/users.py:13" in prompt_text(
        leads[1]
    )  # the guardrail error reached the model


def test_falls_back_to_the_plain_comment_when_the_guardrail_gives_up(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRIES", "1")
    stub = make_stub(["bad 1", "bad 2", "bad 3"])

    result = run_review(monkeypatch, stub)

    assert "`app/users.py:13`" in result.comment and result.comment.startswith(
        "Automated review: 3"
    )


def test_no_findings_means_no_lead_call(monkeypatch):
    def responder(messages, response_model):
        if response_model is not None:
            return {"findings": []}
        return 'Final Answer: {"findings": []}'

    stub = StubLLM(responder=responder)

    result = run_review(monkeypatch, stub)

    assert result.comment == "No issues found in this pull request."
    assert not any(
        "Lead Reviewer" in str(c["messages"][0]["content"]) for c in stub.calls
    )


def test_big_diff_is_reviewed_in_several_chunks(monkeypatch):
    monkeypatch.setenv("MAX_DIFF_TOKENS", "100")
    stub = make_stub([FULL_COMMENT])

    result = run_review(monkeypatch, stub)

    assert result.chunks == 2
    security_calls = [
        c
        for c in stub.calls
        if "Application Security" in str(c["messages"][0]["content"])
    ]
    assert len(security_calls) == 2


def test_empty_diff(monkeypatch):
    result = review.review_diff("", "x")
    assert result.chunks == 0 and "empty" in result.comment


def test_agents_get_limits_and_the_test_reviewer_gets_the_summary_tool(monkeypatch):
    monkeypatch.setenv("MAX_RPM", "7")
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: make_stub())

    reviewers = crew_module.reviewers_crew(DIFF)

    assert reviewers.name == "reviewers_crew"
    assert [a.max_rpm for a in reviewers.agents] == [7, 7, 7]
    assert [t.async_execution for t in reviewers.tasks] == [True, True, False]
    assert [t.name for t in reviewers.agents[2].tools] == ["list_changed_files"]


def test_planning_switch(monkeypatch):
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: make_stub())
    assert crew_module.reviewers_crew(DIFF).planning is False
    monkeypatch.setenv("PLANNING", "true")
    assert crew_module.reviewers_crew(DIFF).planning is True


def test_listener_records_task_events(monkeypatch):
    from crewai.events import crewai_event_bus

    with crewai_event_bus.scoped_handlers():
        listener = ReviewLogListener()
        run_review(monkeypatch, make_stub([FULL_COMMENT]))
        crewai_event_bus.flush()

    assert any(e.startswith("task started") for e in listener.events)
    assert any(e.startswith("task completed") for e in listener.events)


def test_repo_file_tool_is_confined_to_the_root(tmp_path):
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    tool = RepoFileTool(root=root)

    assert tool._run("src/a.py") == "print('hi')"
    assert "outside" in tool._run("../secret.txt")
    assert "does not exist" in tool._run("src/missing.py")


def test_diff_summary_tool_lists_files():
    out = DiffSummaryTool(diff=DIFF)._run()

    assert "app/users.py  +17 -0  code" in out
    assert "tests/test_users.py  +4 -0  TEST" in out
