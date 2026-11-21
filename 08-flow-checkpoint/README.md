# 08 - Flow checkpointing and resume

## 1. What the project does

A three-step flow (`fetch` -> `transform` -> `report`). Step 2 can fail. A checkpoint is written after every finished step, so the rerun continues from step 2 and does **not** repeat step 1.

```
run --fail   ->  step 1 fetch OK (checkpoint) -> step 2 transform FAILS
resume       ->  step 1 is skipped            -> step 2 -> step 3 -> result
```

No LLM is used: the feature belongs to `Flow`, and a step that runs a crew or an agent is saved the same way (that is where it pays off, because step 1 would have cost tokens).

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `Flow(checkpoint=CheckpointConfig(...))` writes a snapshot per finished method | `flow.py` (`run_flow`) |
| `on_events=["method_execution_finished"]`, required for flows | `flow.py` (`checkpoint_config`) |
| `Flow.from_checkpoint(CheckpointConfig(restore_from=path))`, then edit state, then `kickoff()` | `flow.py` (`resume_flow`) |
| Picking the newest checkpoint file by modification time | `flow.py` (`latest_checkpoint`) |
| Offline tests (no model, no key) | `tests/test_flow.py` |

### Checkpoint vs `@persist`

| | `@persist` (project 02 style) | Checkpointing (this project) |
|---|---|---|
| Saves | the state model | a run snapshot: state, finished methods, outputs |
| Resume | `kickoff(restore_from_state_id=id)` | `from_checkpoint(CheckpointConfig(restore_from=file))` |
| Finished steps on resume | run again from `@start` | **skipped** |
| Use for | state that outlives a run (sessions, counters) | continuing one run after a crash |

Things worth knowing (verified on crewai 1.15.44):

- **A flow needs `on_events=["method_execution_finished"]`.** The default (`task_completed`) writes no file for a flow.
- **The checkpoint stores the state, including the cause of the failure.** Resuming as is fails again. Load the flow with `from_checkpoint`, fix the state (here `flow.state.fail = False`), then call `kickoff()`. `kickoff(from_checkpoint=...)` is the shortcut for "resume without changes".
- **Resume does not continue past a `@router`.** A checkpoint taken after a router finished returns the label and runs nothing. Keep crash-prone steps before routers. This flow has no router.
- **File names are `<timestamp>_<id>_p-<parent>.json` with a one-second timestamp**, so sorting names can pick an older file. Use the modification time.
- **Very fast steps can crash the checkpoint writer** (`dictionary changed size during iteration`, a race inside crewai 1.15.44, about 1 run in 4). Each step here sleeps `STEP_SECONDS` (default 0.3 s) like real work, which avoids it.
- `max_checkpoints=N` prunes old files; `provider=SqliteProvider()` stores everything in one database file.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 08-flow-checkpoint
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

No API key and no model are needed. Run, from `08-flow-checkpoint/`:

```bash
uv run checkpoint_run run --fail    # step 2 fails; a checkpoint file is written
uv run checkpoint_run list          # path of the newest checkpoint
uv run checkpoint_run resume        # step 1 is skipped; steps 2 and 3 run
uv run checkpoint_run run           # for comparison: all three steps, no failure
```

Checkpoint files go to `.checkpoints/` (change with `CHECKPOINT_DIR`). CrewAI's own CLI can inspect them: `crewai checkpoint list .checkpoints`.

Tests (offline), from the repository root:

```bash
uv run --package flow-checkpoint pytest 08-flow-checkpoint/tests
```
