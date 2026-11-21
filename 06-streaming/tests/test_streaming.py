from streaming_demo import llm_factory
from streaming_demo.crew import build_crew
from streaming_demo.flow import ExplainFlow
from stub_llm import StubLLM

ANSWER = "Bees make honey. They also pollinate crops."


def use_stub(monkeypatch) -> StubLLM:
    stub = StubLLM(responder=lambda messages, response_model: f"Final Answer: {ANSWER}")
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    return stub


def test_stream_true_returns_a_streaming_output_with_the_final_result(monkeypatch):
    use_stub(monkeypatch)

    streaming = build_crew(stream=True).kickoff(inputs={"topic": "bees"})
    chunks = list(streaming)  # consuming the stream runs the crew to the end

    assert streaming.is_completed
    assert streaming.result.raw == ANSWER
    assert all(hasattr(c, "content") for c in chunks)


def test_stream_false_returns_the_normal_output(monkeypatch):
    use_stub(monkeypatch)

    result = build_crew(stream=False).kickoff(inputs={"topic": "bees"})

    assert result.raw == ANSWER


def test_flow_stream_carries_method_events_and_the_flow_result(monkeypatch):
    use_stub(monkeypatch)

    streaming = ExplainFlow(stream=True).kickoff(inputs={"topic": "bees"})
    frames = list(streaming)

    types = [f.type for f in frames]
    assert "method_execution_started" in types and "flow_finished" in types
    assert streaming.result == "[7 words]"


def test_llm_stream_flag_is_passed_to_the_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")
    assert llm_factory.make_llm(stream=True).stream is True
    assert llm_factory.make_llm().stream is False
