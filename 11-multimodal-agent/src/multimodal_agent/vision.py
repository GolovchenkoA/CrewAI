"""Image input: an image becomes an `image_url` content block in a normal chat message."""

import base64
import mimetypes
from pathlib import Path

from crewai.tools import BaseTool, tool


def image_message(path: str, question: str) -> list[dict]:
    """One user message that holds the question and the image (as a base64 data URL)."""
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"image not found: {path}")
    mime = mimetypes.guess_type(file.name)[0] or "image/png"
    data = base64.b64encode(file.read_bytes()).decode()
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{data}"},
                },
            ],
        }
    ]


def make_vision_tool(vision_llm) -> BaseTool:
    """A tool that lets a text agent look at an image through a vision model."""

    @tool("look_at_image")
    def look_at_image(image_path: str, question: str) -> str:
        """Look at the image file at image_path and answer the question about it."""
        try:
            return str(vision_llm.call(image_message(image_path, question)))
        except FileNotFoundError as exc:
            return str(exc)  # the agent can read the error and correct the path

    return look_at_image
