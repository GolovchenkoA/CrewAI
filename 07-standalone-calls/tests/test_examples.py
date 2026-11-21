from standalone_calls import examples, llm_factory
from standalone_calls.examples import City, WordReport, word_counter
from stub_llm import StubLLM, prompt_text, tool_call


def use(monkeypatch, stub: StubLLM) -> StubLLM:
    monkeypatch.setattr(llm_factory, "make_llm", lambda *a, **k: stub)
    return stub


def test_plain_call_returns_text(monkeypatch):
    stub = use(
        monkeypatch, StubLLM(default_response="A hash map stores key-value pairs.")
    )

    assert (
        examples.plain_call("What is a hash map?")
        == "A hash map stores key-value pairs."
    )
    assert "hash map" in prompt_text(stub.calls[0])


def test_structured_call_returns_a_model_instance(monkeypatch):
    stub = use(
        monkeypatch,
        StubLLM(
            responses=[
                {"name": "Warsaw", "country": "Poland", "population_millions": 1.8}
            ]
        ),
    )

    city = examples.structured_call("Tell me about Warsaw.")

    assert city == City(name="Warsaw", country="Poland", population_millions=1.8)
    assert stub.calls[0]["response_model"] is City


def test_agent_kickoff_runs_the_tool_and_returns_structured_output(monkeypatch):
    text = "CrewAI agents can run without a crew"
    stub = use(
        monkeypatch,
        StubLLM(
            responses=[
                tool_call("word_counter", {"text": text}),
                "Final Answer: The text has 7 words.",
                {"text": text, "word_count": 7},  # the conversion to WordReport
            ]
        ),
    )

    out = examples.agent_with_tool(text)

    assert out.pydantic == WordReport(text=text, word_count=7)
    assert "Observation: 7" in prompt_text(
        stub.calls[1]
    )  # the real tool ran and its result went back


def test_tool_counts_words():
    assert word_counter.run(text="one two three") == 3
