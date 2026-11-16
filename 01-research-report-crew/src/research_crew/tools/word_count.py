from crewai.tools import tool


@tool("Word Count")
def word_count(text: str) -> str:
    """Count the words and Markdown headings in a text. Use it to check report length."""
    words = len(text.split())
    headings = sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))
    return f"{words} words, {headings} headings"
