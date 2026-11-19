"""The triage flow.

            +-> classify ------+
ingest -----+                  +-> route --> handle_billing / handle_bug / handle_howto
            +-> analyze_sentiment            |
                                             v
                              review_gate --> publish_auto ----------------+
                                   |                                       +--> finalize
                                   +--> request_review -> apply_review ----+
                                        (human in the loop, low confidence)
"""

import json
import os
from pathlib import Path
from typing import Literal

from crewai import Memory
from crewai.flow import (
    Flow,
    HumanFeedbackResult,
    and_,
    human_feedback,
    listen,
    or_,
    persist,
    router,
    start,
)
from crewai.flow.persistence import SQLiteFlowPersistence
from pydantic import BaseModel

from triage_flow import crews, llm_factory


class TicketState(BaseModel):
    # input
    ticket_id: str = ""
    customer_id: str = ""
    subject: str = ""
    body: str = ""
    # memory
    customer_context: str = ""
    # classifier and sentiment crews
    category: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    sentiment: str = ""
    urgency: str = ""
    # specialist crew and review
    draft: str = ""
    final_reply: str = ""
    human_reviewed: bool = False


class TriageFeedbackProvider:
    """Collects the human decision for low-confidence tickets.

    HITL_MODE=console (default) asks on the terminal, HITL_MODE=auto approves the draft without asking
    (for unattended runs). Tests can queue answers in `answers`.
    """

    def __init__(self) -> None:
        self.answers: list[str] = []

    def request_feedback(self, context, flow) -> str:
        if self.answers:
            return self.answers.pop(0)
        if os.getenv("HITL_MODE", "console").strip().lower() == "auto":
            return ""
        print(f"\n--- Human review needed (ticket {flow.state.ticket_id}) ---")
        print(
            f"Category guess: {flow.state.category} (confidence {flow.state.confidence:.2f})"
        )
        print(
            f"Customer wrote: {flow.state.body}\n\nDraft reply:\n{context.method_output}\n"
        )
        return input("Press Enter to approve, or type the corrected reply: ")


FEEDBACK = TriageFeedbackProvider()
_DB = Path(os.getenv("FLOW_DB", "db/flow_states.db"))
_DB.parent.mkdir(parents=True, exist_ok=True)


@persist(SQLiteFlowPersistence(str(_DB)))
class TriageFlow(Flow[TicketState]):
    # --- 1. ingest (+ memory: what do we know about this customer?) ---------------------------------
    @start()
    def ingest(self):
        if llm_factory.env_bool("USE_MEMORY", True):
            try:
                matches = self.recall(
                    f"previous tickets of customer {self.state.customer_id}",
                    scope=f"/customers/{self.state.customer_id}",
                    limit=3,
                )
                self.state.customer_context = "\n".join(
                    m.record.content for m in matches
                )
            except (
                Exception
            ) as exc:  # memory is a helper, never a reason to lose the ticket
                print(f"[memory] recall failed: {exc}")
        return self.state.ticket_id

    # --- 2. two parallel branches ---------------------------------------------------------------------
    @listen(ingest)
    def classify(self):
        result = crews.classifier_crew().kickoff(inputs=crews.ticket_inputs(self.state))
        assert result.pydantic is not None, "classifier returned no structured output"
        self.state.category = result.pydantic.category
        self.state.confidence = result.pydantic.confidence
        self.state.reasoning = result.pydantic.reasoning

    @listen(ingest)
    def analyze_sentiment(self):
        result = crews.sentiment_crew().kickoff(inputs=crews.ticket_inputs(self.state))
        assert result.pydantic is not None, (
            "sentiment crew returned no structured output"
        )
        self.state.sentiment = result.pydantic.sentiment
        self.state.urgency = result.pydantic.urgency

    # --- 3. route by category -------------------------------------------------------------------------
    @router(and_(classify, analyze_sentiment))
    def route(self) -> Literal["billing", "bug", "how_to"]:
        return self.state.category.replace("-", "_")  # type: ignore[return-value]

    @listen("billing")
    def handle_billing(self):
        self._draft("billing")

    @listen("bug")
    def handle_bug(self):
        self._draft("bug")

    @listen("how_to")
    def handle_howto(self):
        self._draft("how_to")

    def _draft(self, category: str) -> None:
        result = crews.specialist_crew(category).kickoff(
            inputs=crews.ticket_inputs(self.state)
        )
        self.state.draft = result.raw

    # --- 4. confidence gate and human in the loop -----------------------------------------------------
    @router(or_(handle_billing, handle_bug, handle_howto))
    def review_gate(self) -> Literal["auto_send", "human_review"]:
        threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        return "auto_send" if self.state.confidence >= threshold else "human_review"

    @listen("auto_send")
    def publish_auto(self):
        self.state.final_reply = self.state.draft

    @listen("human_review")
    @human_feedback(
        message="Low classification confidence. Press Enter to approve the draft, or type the corrected reply.",
        provider=FEEDBACK,
    )
    def request_review(self):
        return self.state.draft  # shown to the human as the output under review

    @listen(request_review)
    def apply_review(self, result: HumanFeedbackResult):
        self.state.human_reviewed = True
        edited = (result.feedback or "").strip()
        self.state.final_reply = edited or self.state.draft

    # --- 5. write results, remember the customer ------------------------------------------------------
    @listen(or_(publish_auto, apply_review))
    def finalize(self):
        out_dir = Path(os.getenv("OUTPUT_DIR", "output")) / self.state.ticket_id
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "reply.md").write_text(self.state.final_reply, encoding="utf-8")
        (out_dir / "ticket.json").write_text(
            json.dumps(self.state.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if llm_factory.env_bool("USE_MEMORY", True):
            try:
                self.remember(
                    f"Ticket {self.state.ticket_id} ({self.state.category}, {self.state.sentiment}): "
                    f"{self.state.subject}. Reply sent: {self.state.final_reply[:300]}",
                    scope=f"/customers/{self.state.customer_id}",
                )
            except Exception as exc:
                print(f"[memory] remember failed: {exc}")
        return self.state.final_reply


def build_flow() -> TriageFlow:
    """A fresh flow; Memory (local embedder) is attached unless USE_MEMORY=false."""
    if llm_factory.env_bool("USE_MEMORY", True):
        memory = Memory(
            llm=llm_factory.make_llm(),
            embedder=llm_factory.embedder_config(),
            storage="lancedb",
        )
        return TriageFlow(memory=memory)
    return TriageFlow()
