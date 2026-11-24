import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from crewai.events import crewai_event_bus
from crewai_tools import FileReadTool
from crewai_tools.tools.scrape_website_tool import scrape_website_tool
from stock_tools.agent import ToolLog, default_tools, research
from stub_llm import StubLLM, prompt_text, tool_call

SAMPLE = Path(__file__).parents[1] / "samples" / "release_notes.txt"
NOTES = "release_notes.txt"  # FileReadTool reads only below the current directory
URL = "https://example.test/page"


@pytest.fixture(autouse=True)
def notes_in_cwd():
    shutil.copy(
        SAMPLE, NOTES
    )  # the autouse conftest fixture already moved us into a temp dir


def fake_page(url, **kwargs):
    html = "<html><body><h1>Example Domain</h1><p>Some text.</p></body></html>"
    return SimpleNamespace(text=html, apparent_encoding="utf-8", encoding=None)


def test_file_read_tool_reads_the_local_file():
    text = FileReadTool().run(file_path=NOTES)

    assert "Version 2.3.0" in text and "--dry-run" in text


def test_default_tools_are_the_two_stock_tools():
    assert [t.name for t in default_tools()] == [
        "Read a file's content",
        "Read website content",
    ]


def test_agent_uses_both_tools_and_gets_their_real_output(monkeypatch):
    monkeypatch.setattr(scrape_website_tool, "safe_get", fake_page)  # no network
    log = ToolLog()
    llm = StubLLM(
        responses=[
            tool_call("Read a file's content", {"file_path": NOTES}),
            tool_call("Read website content", {"website_url": URL}),
            "Final Answer: 2.3.0 added --dry-run. Heading: Example Domain.",
        ]
    )

    answer = research(NOTES, URL, llm=llm)
    crewai_event_bus.flush()

    assert answer == "2.3.0 added --dry-run. Heading: Example Domain."
    assert "Deprecated: the --legacy flag" in prompt_text(
        llm.calls[1]
    )  # file content went back
    assert "Example Domain" in prompt_text(llm.calls[2])  # page text went back
    assert log.calls == ["read_a_files_content", "read_website_content"]


def test_file_read_tool_refuses_paths_outside_the_working_directory():
    assert "outside the allowed directory" in FileReadTool().run(file_path=str(SAMPLE))
