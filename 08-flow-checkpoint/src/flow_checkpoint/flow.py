"""A three-step flow. Step 2 can fail; a checkpoint lets the rerun skip step 1."""

import glob
import os
import time

from crewai import CheckpointConfig
from crewai.flow import Flow, listen, start
from pydantic import BaseModel

# Each step takes a moment, like real work. Without it the steps finish within milliseconds and
# crewai's checkpoint writer sometimes crashes ("dictionary changed size during iteration") while
# event handlers are still adding events (seen on crewai 1.15.44).
STEP_SECONDS = float(os.getenv("STEP_SECONDS", "0.3"))


def say(message: str) -> None:
    print(message, flush=True)


class PipelineState(BaseModel):
    fail: bool = False  # step 2 raises while this is True
    rows: list[int] = []


class PipelineFlow(Flow[PipelineState]):
    @start()
    def fetch(self):
        say("step 1 fetch: running (pretend this is slow or costs tokens)")
        time.sleep(STEP_SECONDS)
        self.state.rows = [1, 2, 3]

    @listen(fetch)
    def transform(self):
        say("step 2 transform: running")
        time.sleep(STEP_SECONDS)
        if self.state.fail:
            raise RuntimeError("the database is down")
        self.state.rows = [r * 10 for r in self.state.rows]

    @listen(transform)
    def report(self):
        say("step 3 report: running")
        time.sleep(STEP_SECONDS)
        return f"total = {sum(self.state.rows)}"


def checkpoint_config(location: str) -> CheckpointConfig:
    # A flow needs "method_execution_finished": the default ("task_completed") writes nothing for a flow.
    return CheckpointConfig(location=location, on_events=["method_execution_finished"])


def latest_checkpoint(location: str) -> str | None:
    """Newest file by mtime: names have a one-second timestamp, so sorting names can pick an older one."""
    files = glob.glob(os.path.join(location, "**", "*.json"), recursive=True)
    return max(files, key=os.path.getmtime) if files else None


def run_flow(location: str, fail: bool) -> str:
    flow = PipelineFlow(checkpoint=checkpoint_config(location))
    return flow.kickoff(inputs={"fail": fail})


def resume_flow(location: str, path: str | None = None, fix: bool = True) -> str:
    """Continue from a checkpoint; completed steps are skipped."""
    path = path or latest_checkpoint(location)
    if path is None:
        raise FileNotFoundError(f"no checkpoint found under {location!r}")
    flow = PipelineFlow.from_checkpoint(CheckpointConfig(restore_from=path))
    if fix:
        # The checkpoint stores the state, so the failure condition is restored too: clear it first.
        flow.state.fail = False
    return flow.kickoff()
