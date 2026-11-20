"""Event listener: logs task, tool and failure events of a review (BaseEventListener).

Instantiate once per process (main.py and api.py do); handlers run on worker threads.
"""

import logging

from crewai.events import (
    BaseEventListener,
    LLMCallFailedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    ToolUsageErrorEvent,
    ToolUsageFinishedEvent,
)

log = logging.getLogger("code_review.events")


class ReviewLogListener(BaseEventListener):
    def __init__(self) -> None:
        self.events: list[str] = []  # also kept in memory: handy in tests
        super().__init__()

    def _note(self, message: str) -> None:
        self.events.append(message)
        log.info(message)

    def setup_listeners(self, crewai_event_bus) -> None:
        @crewai_event_bus.on(TaskStartedEvent)
        def on_task_start(source, event) -> None:
            self._note(f"task started: {event.task_name or event.task_id}")

        @crewai_event_bus.on(TaskCompletedEvent)
        def on_task_done(source, event) -> None:
            self._note(f"task completed: {event.task_name or event.task_id}")

        @crewai_event_bus.on(TaskFailedEvent)
        def on_task_failed(source, event) -> None:
            log.error(
                "task failed: %s: %s", event.task_name or event.task_id, event.error
            )
            self.events.append(f"task failed: {event.error}")

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool(source, event) -> None:
            self._note(f"tool used: {event.tool_name} by {event.agent_role}")

        @crewai_event_bus.on(ToolUsageErrorEvent)
        def on_tool_error(source, event) -> None:
            log.warning("tool error: %s", event)

        @crewai_event_bus.on(LLMCallFailedEvent)
        def on_llm_failed(source, event) -> None:
            log.error("LLM call failed: %s", event.error)
            self.events.append(f"llm failed: {event.error}")
