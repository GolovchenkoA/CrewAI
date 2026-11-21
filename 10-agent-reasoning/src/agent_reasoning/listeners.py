"""Record what the planner did: the plan, its steps, failures, and the number of LLM calls."""

from crewai.events import (
    BaseEventListener,
    LLMCallCompletedEvent,
    ToolUsageFinishedEvent,
)
from crewai.events.types.observation_events import PlanStepStartedEvent
from crewai.events.types.reasoning_events import (
    AgentReasoningCompletedEvent,
    AgentReasoningFailedEvent,
)

# The planner asks the model to call this function; its arguments carry the structured steps.
PLAN_TOOLS = {"create_reasoning_plan", "create_plan", "refine_plan"}


class ReasoningLog(BaseEventListener):
    def __init__(self) -> None:
        self.plans: list[tuple[str, bool]] = []  # (summary, ready)
        self.planned_steps: list[str] = []  # steps from the latest plan
        self.executed_steps: list[str] = []  # steps the executor started
        self.errors: list[str] = []
        self.llm_calls = 0
        super().__init__()

    def setup_listeners(self, crewai_event_bus) -> None:
        @crewai_event_bus.on(AgentReasoningCompletedEvent)
        def on_plan(source, event) -> None:
            self.plans.append((event.plan, event.ready))

        @crewai_event_bus.on(AgentReasoningFailedEvent)
        def on_failed(source, event) -> None:
            self.errors.append(event.error)

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_plan_tool(source, event) -> None:
            if event.tool_name not in PLAN_TOOLS:
                return
            args = event.tool_args if isinstance(event.tool_args, dict) else {}
            self.planned_steps = [
                f"{step.get('step_number', i + 1)}. {step.get('description', '')}"
                for i, step in enumerate(args.get("steps") or [])
            ]

        @crewai_event_bus.on(PlanStepStartedEvent)
        def on_step(source, event) -> None:
            self.executed_steps.append(f"{event.step_number}. {event.step_description}")

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def on_llm(source, event) -> None:
            self.llm_calls += 1
