from conversational_flow.flow import build_flow
from stub_llm import StubLLM, prompt_text


def chat(stub: StubLLM | None = None, db: str = "chat.db"):
    stub = stub or StubLLM(default_response="stub reply")
    return build_flow(llm=stub, db_path=db), stub


def test_name_route_is_deterministic_and_stores_state():
    flow, stub = chat()

    reply = flow.handle_turn("Hi, my name is ada", session_id="s1")

    assert reply == "Nice to meet you, Ada!"
    assert flow.state.customer_name == "Ada"
    assert stub.calls == []  # a custom route does not call the model


def test_converse_route_sends_the_history_to_the_model():
    flow, stub = chat()

    flow.handle_turn("my name is Ada", session_id="s1")
    reply = flow.handle_turn("What is the capital of Poland?", session_id="s1")

    assert reply == "stub reply"
    sent = prompt_text(stub.calls[-1])
    assert "my name is Ada" in sent  # an earlier turn is part of the prompt
    assert "What is the capital of Poland?" in sent
    assert [m.role for m in flow.state.messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_end_route_closes_the_conversation_without_the_model():
    flow, stub = chat()

    assert flow.handle_turn("bye", session_id="s1") == "Conversation ended."
    assert flow.state.ended and stub.calls == []


def test_state_survives_a_new_flow_object_and_stays_per_session():
    flow, _ = chat()
    flow.handle_turn("my name is Ada", session_id="alice")
    flow.handle_turn("how are you?", session_id="alice")

    # a new object on the same database = a restarted process
    again, _ = chat()
    again.handle_turn("still there?", session_id="alice")
    assert again.state.customer_name == "Ada"
    assert again.state.turns == 3
    assert len(again.state.messages) == 6

    other, _ = chat()
    other.handle_turn("hello", session_id="bob")
    assert other.state.customer_name == "" and other.state.turns == 1
    assert len(other.state.messages) == 2
