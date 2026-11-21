import pytest
from flow_checkpoint import flow as flow_module
from flow_checkpoint.flow import latest_checkpoint, resume_flow, run_flow


@pytest.fixture
def steps(monkeypatch) -> list[str]:
    """Record which steps ran (the flow reports 'step N name: ...' through say())."""
    seen: list[str] = []
    monkeypatch.setattr(flow_module, "say", lambda m: seen.append(m.split(":")[0]))
    return seen


def test_run_without_failure_runs_all_steps(steps):
    assert run_flow(".cp", fail=False) == "total = 60"
    assert steps == ["step 1 fetch", "step 2 transform", "step 3 report"]


def test_failed_run_writes_a_checkpoint(steps):
    with pytest.raises(RuntimeError, match="database is down"):
        run_flow(".cp", fail=True)

    assert latest_checkpoint(".cp") is not None
    assert steps == ["step 1 fetch", "step 2 transform"]


def test_resume_skips_the_finished_step(steps):
    with pytest.raises(RuntimeError):
        run_flow(".cp", fail=True)
    steps.clear()

    assert (
        resume_flow(".cp") == "total = 60"
    )  # the rows of step 1 came from the checkpoint
    assert steps == ["step 2 transform", "step 3 report"]  # no "step 1 fetch"


def test_resume_without_fix_fails_again(steps):
    with pytest.raises(RuntimeError):
        run_flow(".cp", fail=True)

    with pytest.raises(RuntimeError, match="database is down"):
        resume_flow(".cp", fix=False)  # the failure flag is part of the saved state


def test_resume_without_checkpoint_is_a_clear_error():
    with pytest.raises(FileNotFoundError):
        resume_flow(".cp")
