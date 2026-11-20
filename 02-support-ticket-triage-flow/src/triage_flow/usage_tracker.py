"""Token usage per crew and per agent, collected from CrewAI events.

Why events and not ``CrewOutput.token_usage``: that counter is summed over each LLM
object's whole lifetime, so a shared or reused LLM double-counts and mixes runs. One
``LLMCallCompletedEvent`` is emitted per model call, so adding them up is exact and also
covers guardrail retries and delegation.

Usage::

    tracker = UsageTracker()      # create once per run, before kickoff
    flow.kickoff()
    print(tracker.report())

Every crew must have a ``name`` (``Crew(name="billing_crew", ...)``): that is the "team" label.
Crews of one flow run one after another; calls made outside any crew show up as ``(no crew)``.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass

from crewai.types.usage_metrics import UsageMetrics
from crewai.events import (
    BaseEventListener,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
    CrewKickoffStartedEvent,
    LLMCallCompletedEvent,
    crewai_event_bus,
)

NO_CREW = "(no crew)"
NO_AGENT = "(no agent)"


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    requests: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.requests += 1


class UsageTracker(BaseEventListener):
    def __init__(self) -> None:
        # state first: super().__init__() registers the handlers immediately
        self._lock = threading.Lock()
        self._crew_stack: list[str] = []
        self.by_agent: dict[tuple[str, str], Usage] = defaultdict(Usage)
        super().__init__()

    def setup_listeners(self, crewai_event_bus) -> None:  # noqa: ANN001
        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_crew_start(source, event) -> None:  # noqa: ANN001
            with self._lock:
                self._crew_stack.append(event.crew_name or "crew")

        def on_crew_end(source, event) -> None:  # noqa: ANN001
            with self._lock:
                if self._crew_stack:
                    self._crew_stack.pop()

        crewai_event_bus.on(CrewKickoffCompletedEvent)(on_crew_end)
        crewai_event_bus.on(CrewKickoffFailedEvent)(on_crew_end)

        @crewai_event_bus.on(LLMCallCompletedEvent)
        def on_llm_call(source, event) -> None:  # noqa: ANN001
            # providers name the keys differently (Anthropic: input_tokens / output_tokens,
            # OpenAI/Ollama: prompt_tokens / completion_tokens): let CrewAI normalise them
            metrics = UsageMetrics.from_provider_dict(event.usage)
            prompt = metrics.prompt_tokens if metrics else 0
            completion = metrics.completion_tokens if metrics else 0
            with self._lock:
                crew = self._crew_stack[-1] if self._crew_stack else NO_CREW
                agent = event.agent_role or NO_AGENT
                self.by_agent[(crew, agent)].add(prompt, completion)

    # ---- reading the numbers ----

    def by_crew(self) -> dict[str, Usage]:
        crews: dict[str, Usage] = defaultdict(Usage)
        for (crew, _), u in self.snapshot().items():
            total = crews[crew]
            total.prompt_tokens += u.prompt_tokens
            total.completion_tokens += u.completion_tokens
            total.requests += u.requests
        return dict(crews)

    def snapshot(self) -> dict[tuple[str, str], Usage]:
        crewai_event_bus.flush()  # handlers run on worker threads
        with self._lock:
            return {k: Usage(v.prompt_tokens, v.completion_tokens, v.requests) for k, v in self.by_agent.items()}

    def total(self) -> Usage:
        total = Usage()
        for u in self.by_crew().values():
            total.prompt_tokens += u.prompt_tokens
            total.completion_tokens += u.completion_tokens
            total.requests += u.requests
        return total

    def report(self) -> str:
        agents = self.snapshot()
        if not agents:
            return "Token usage: no LLM calls recorded."
        lines = ["Token usage", f"{'':<34}{'total':>9}{'prompt':>9}{'compl.':>9}{'calls':>7}"]
        for crew, cu in sorted(self.by_crew().items()):
            lines.append(_row(crew, cu))
            members = sorted((a, u) for (c, a), u in agents.items() if c == crew)
            for i, (agent, u) in enumerate(members):
                branch = "└─" if i == len(members) - 1 else "├─"
                lines.append(_row(f"  {branch} {agent}", u))
        lines.append(_row("TOTAL", self.total()))
        return "\n".join(lines)


def _row(label: str, u: Usage) -> str:
    return f"{label:<34}{u.total_tokens:>9,}{u.prompt_tokens:>9,}{u.completion_tokens:>9,}{u.requests:>7}"
