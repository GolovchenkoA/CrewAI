# 10 - Agent reasoning (planning)

## 1. What the project does

One agent, one multi-step task (a 2-day budget trip to Krakow), run twice:

| Mode | What happens | Live result (`qwen3.5:9b`) |
|---|---|---|
| `plain` | the agent answers directly | 1 LLM call, 64 s, 2.2k tokens |
| `reasoning` | the agent first **plans** (a list of steps), then runs each step, then writes the answer | 6 LLM calls, 108 s, 7.6k tokens |

The script prints the plan, the planned steps, the steps the executor actually started, the answer, and the cost (time, LLM calls, tokens). The point: planning is not free. It adds calls and tokens, and it pays off on tasks where the agent can lose track of parts of the request.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| Agent-level planning: `Agent(planning_config=PlanningConfig(...))` | `agent.py` |
| `reasoning_effort`, `max_attempts`, `max_steps`, `step_timeout` | `agent.py` |
| Logging the reasoning through events (`AgentReasoningCompletedEvent`, the planner's `create_reasoning_plan` function call, `PlanStepStartedEvent`, `LLMCallCompletedEvent`) | `listeners.py` |
| Comparing a run with and without planning | `main.py` (`--mode both`) |
| Offline tests with a stub LLM | `tests/test_reasoning.py` |

**Agent reasoning vs crew planning.** `Agent(planning_config=...)` makes **one agent** plan its own work for its own task. `Crew(planning=True)` is different: a separate planner writes a plan for the **whole crew** and adds it to every task. `Agent(reasoning=True)` and `max_reasoning_attempts` are deprecated aliases of `planning_config`.

Things worth knowing (crewai 1.15.44):

- **`reasoning_effort`**: `low` checks each step with a heuristic (no extra LLM call), `medium` (default) asks the model to observe each step and replans on failure, `high` can also refine the plan or finish early. This project uses `low`; change it with `--effort`.
- **Bound the planning.** With `max_attempts=None` the agent keeps refining until the model says it is ready; a small model may never do that and the run seems to hang (`qwen3:4b` ran for 8 minutes without finishing). The project sets `max_attempts=2`.
- **The plan comes from a function call.** The planner asks the model to call `create_reasoning_plan` with `plan`, `steps` and `ready`. The steps are only executed one by one when `ready` is true; otherwise the agent just answers with the plan in mind.
- **The model must be reliable at this.** `llama3.1:8b` answered `ready: "NOT READY"` (a string, not a boolean), so planning failed with a validation error (`AgentReasoningFailedEvent`) and the agent fell back to a plain answer. `qwen3.5:9b` worked every time. The listener shows such failures as `PLANNING FAILED`.
- Planning failures do not stop the task; the agent still answers, only without a plan.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 10-agent-reasoning
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3.5:9b` (6.6 GB; smaller models were not reliable for planning, see above).

Run, from `10-agent-reasoning/` (a run takes 1 to 3 minutes locally):

```bash
uv run reasoning_run                          # plain, then with reasoning, side by side
uv run reasoning_run --mode reasoning         # only the planning run
uv run reasoning_run --effort medium          # observe each step with the model
uv run reasoning_run --task "Plan a 3-day trip to Gdansk for a family with two kids."
```

Tests (offline, no model needed), from the repository root:

```bash
uv run --package agent-reasoning pytest 10-agent-reasoning/tests
```
