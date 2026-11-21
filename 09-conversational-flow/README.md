# 09 - Conversational flow

## 1. What the project does

A console chat where **every user message is one `handle_turn()` call** with a session id, instead of a one-shot `kickoff()`. The session id selects the stored state, so a chat can continue after the program was restarted.

The flow has three routes:

| Message | Route | Handled by |
|---|---|---|
| "... my name is Ada" | `NAME` | our `@listen("NAME")` method: stores `customer_name`, no model call |
| "bye" / "goodbye" | `end` | built-in terminator, no model call |
| anything else | `converse` | built-in handler: the LLM answers from the whole message history |

State per session (`ChatState`): `messages` (the history) and `id` come from `ConversationState`; `customer_name` and `turns` are ours.

## 2. CrewAI aspects covered

| Aspect | Where |
|---|---|
| `@ConversationConfig(llm=..., system_prompt=...)` makes a flow conversational | `flow.py` |
| `handle_turn(message, session_id=...)`: one turn per call | `main.py` (`--say`) |
| `flow.chat(session_id=...)`: a ready-made terminal chat loop | `main.py` |
| `route_turn()`: deterministic routing, labels match `@listen("LABEL")` | `flow.py` |
| Built-in `converse` and `end` routes | not written by us |
| State kept per session: `ConversationState` subclass plus `@persist` (SQLite) | `flow.py` |
| Offline tests with a stub LLM | `tests/test_chat.py` |

Things worth knowing (crewai 1.15.44):

- **The conversational API is experimental.** Pin the CrewAI version (this project uses `~=1.15.44`). The module `crewai.experimental.conversational` is a deprecated alias of `crewai.flow`.
- Do not call `kickoff(user_message=...)`: it raises `TypeError`. `handle_turn()` is the chat wrapper; it stores the user line in `state.messages` before the graph runs, so a handler must not add it again.
- A handler that returns a string has that string recorded as the assistant message.
- **State is restored by session id only with persistence.** Without `@persist` each `handle_turn()` on a new flow object starts from an empty state. Here `@persist` is on the class (fine for a flow this small); for bigger flows put it on one terminal step.
- The LLM is part of the class config (`ConversationConfig(llm=...)`), so `build_flow()` creates the class inside a function. Tests pass a stub LLM there.
- Without an `llm`, the `converse` route answers "I can continue the conversation once an LLM is configured."
- `@human_feedback` is not for follow-up chat; it approves one step's output. Use another `handle_turn()`.
- Tracing: `finalize_session_traces()` closes the session trace. `chat()` does it for you; the `--say` mode calls it in `try/finally`.

## 3. Prepare, build, run

This project is a member of the **uv workspace** in the repository root (one shared `.venv` and `uv.lock`). First-time setup on a new computer: see the [root README](../README.md#setting-up-on-another-computer).

```bash
cd <repo-root>
uv sync
cd 09-conversational-flow
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

Choose the LLM in `.env`: `LLM_PROVIDER=claude` with `ANTHROPIC_API_KEY` (or the same OS environment variable), or `LLM_PROVIDER=local` with `ollama pull qwen3:4b` (2.5 GB, a small model that is good enough for this demo).

Run, from `09-conversational-flow/`:

```bash
uv run chat_run                                  # interactive chat, session "demo"; type exit to quit
uv run chat_run --session alice                  # another session has its own history and state
uv run chat_run --session alice --say "Hi, my name is Ada" "What is the capital of Poland?"
uv run chat_run --session alice --say "Do you remember my name?"   # a new process, same session: it does
```

Session state is stored in `.chat/sessions.db` (change with `CHAT_DB`). Delete the file to start over.

Tests (offline, no model needed), from the repository root:

```bash
uv run --package conversational-flow pytest 09-conversational-flow/tests
```
