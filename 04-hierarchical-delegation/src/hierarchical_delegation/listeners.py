"""Record every delegation: which coworker the manager picked for which task."""

import json

from crewai.events import BaseEventListener, ToolUsageFinishedEvent

# the finished event reports the snake_case tool name, the started event the display name
DELEGATION_TOOLS = {"delegate_work_to_coworker", "ask_question_to_coworker"}


class DelegationLog(BaseEventListener):
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []  # (coworker, task text)
        super().__init__()

    def setup_listeners(self, crewai_event_bus) -> None:
        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool(source, event) -> None:
            if event.tool_name not in DELEGATION_TOOLS:
                return
            args = event.tool_args
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            args = args or {}
            text = str(args.get("task") or args.get("question") or "")
            self.entries.append((str(args.get("coworker", "?")), text))
