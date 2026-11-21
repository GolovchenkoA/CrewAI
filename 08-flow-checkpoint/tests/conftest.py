import os
from pathlib import Path

# Must be set before crewai is imported: SQLite and memory files go here.
os.environ["CREWAI_STORAGE_DIR"] = str(Path(__file__).parent / ".crewai-test-storage")

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # checkpoints land in a temp dir
