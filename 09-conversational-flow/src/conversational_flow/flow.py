"""A chat flow: each user message is one handle_turn() call; state is kept per session id."""

import os
import re
from pathlib import Path

from crewai.flow import ConversationConfig, ConversationState, Flow, listen, persist
from crewai.flow.persistence import SQLiteFlowPersistence

from conversational_flow.llm_factory import make_llm

SYSTEM_PROMPT = (
    "You are a friendly support assistant. Answer in one or two short sentences. "
    "Use the earlier messages of this conversation when they are relevant."
)
NAME_PATTERN = re.compile(r"\bmy name is (\w+)", re.IGNORECASE)


class ChatState(ConversationState):
    """ConversationState already holds `id` (the session id) and `messages` (the history)."""

    customer_name: str = ""
    turns: int = 0


def default_db_path() -> str:
    return os.getenv("CHAT_DB", ".chat/sessions.db")


def build_flow(llm=None, db_path: str | None = None) -> Flow:
    """Build a chat flow. The class is created here because the LLM is part of its config."""
    db_path = db_path or default_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @persist(
        SQLiteFlowPersistence(db_path)
    )  # state is stored per state.id = session id
    @ConversationConfig(llm=llm or make_llm(), system_prompt=SYSTEM_PROMPT)
    class SupportChat(Flow[ChatState]):
        def route_turn(self, context):
            """Pick a route for this message. Anything not matched goes to the built-in `converse`."""
            self.state.turns += 1
            message = self.state.current_user_message or ""
            if NAME_PATTERN.search(message):
                return "NAME"
            if message.strip().lower() in {"bye", "goodbye"}:
                return "end"
            return "converse"

        @listen("NAME")
        def remember_name(self) -> str:
            """The user tells us their name."""
            match = NAME_PATTERN.search(self.state.current_user_message or "")
            self.state.customer_name = match.group(1).capitalize()
            return f"Nice to meet you, {self.state.customer_name}!"

    return SupportChat()
