import base64
from pathlib import Path

import pytest
from multimodal_agent.agent import ask
from multimodal_agent.vision import image_message, make_vision_tool
from stub_llm import StubLLM, prompt_text, tool_call

SAMPLE = str(Path(__file__).parents[1] / "samples" / "sales_chart.png")


def test_image_message_holds_the_question_and_a_data_url():
    (message,) = image_message(SAMPLE, "What is shown?")

    text_block, image_block = message["content"]
    assert text_block == {"type": "text", "text": "What is shown?"}
    url = image_block["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]).startswith(b"\x89PNG")


def test_missing_image_is_an_error_for_the_caller_and_text_for_the_agent():
    with pytest.raises(FileNotFoundError):
        image_message("nope.png", "?")

    tool = make_vision_tool(StubLLM())
    assert "image not found" in tool.run(image_path="nope.png", question="?")


def test_agent_looks_at_the_image_through_the_vision_model():
    agent_llm = StubLLM(
        responses=[
            tool_call(
                "look_at_image", {"image_path": SAMPLE, "question": "highest bar?"}
            ),
            "Final Answer: Q3 is the highest, with 60 units.",
        ]
    )
    vision_llm = StubLLM(default_response="The tallest bar is Q3 (60).")

    answer = ask(SAMPLE, "Which quarter is highest?", agent_llm, vision_llm)

    assert answer == "Q3 is the highest, with 60 units."
    sent = vision_llm.calls[0]["messages"][0]["content"]
    assert [block["type"] for block in sent] == [
        "text",
        "image_url",
    ]  # the image reached the model
    assert "The tallest bar is Q3 (60)." in prompt_text(
        agent_llm.calls[1]
    )  # and the answer came back
    assert "image_url" not in prompt_text(
        agent_llm.calls[0]
    )  # the text agent never sees the pixels
