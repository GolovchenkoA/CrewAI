import os
import socket
from pathlib import Path

# Must be set before crewai is imported: SQLite/memory files go here, not into the user data dir.
os.environ["CREWAI_STORAGE_DIR"] = str(Path(__file__).parent / ".crewai-test-storage")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    real_connect = socket.socket.connect

    def refuse(self, address, *args, **kwargs):
        # loopback is allowed: asyncio on Windows opens a local socket pair for every event loop
        host = address[0] if isinstance(address, tuple) else address
        if host in ("127.0.0.1", "::1", "localhost"):
            return real_connect(self, address, *args, **kwargs)
        raise RuntimeError(f"test tried to use the network: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.chdir(tmp_path)  # output_file= writes land in a temp dir
    (tmp_path / "notes").mkdir()
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("PROCESS", "sequential")
    monkeypatch.setenv("ALLOW_DELEGATION", "false")
    monkeypatch.setenv("VERBOSE", "false")
    monkeypatch.setenv("MIN_REPORT_WORDS", "20")
