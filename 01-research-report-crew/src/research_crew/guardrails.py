import os
import re
from typing import Any

from crewai import TaskOutput

REQUIRED_SECTIONS = ["Executive Summary", "Key Findings", "Conclusion", "Sources"]


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def report_guardrail(output: TaskOutput) -> tuple[bool, Any]:
    """Accept the editor's report only if it has every required section and enough words."""
    text = _strip_fence(output.raw)
    missing = [
        name
        for name in REQUIRED_SECTIONS
        if not re.search(rf"^#{{1,3}}\s*.*{re.escape(name)}", text, re.IGNORECASE | re.MULTILINE)
    ]
    if missing:
        return (False, f"Missing required Markdown headings: {', '.join(missing)}. Add them.")
    min_words = int(os.getenv("MIN_REPORT_WORDS", "250"))
    words = len(text.split())
    if words < min_words:
        return (False, f"Report has {words} words; it needs at least {min_words}. Expand it.")
    return (True, text)
