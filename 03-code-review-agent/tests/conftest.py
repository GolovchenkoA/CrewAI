import os
import socket
from pathlib import Path

# Must be set before crewai / code_review are imported: SQLite and memory files go here.
os.environ["CREWAI_STORAGE_DIR"] = str(Path(__file__).parent / ".crewai-test-storage")

import pytest


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
    monkeypatch.chdir(tmp_path)
    for name, value in {
        "LLM_PROVIDER": "local",
        "PLANNING": "false",
        "VERBOSE": "false",
        "MAX_DIFF_TOKENS": "6000",
        "GITHUB_TOKEN": "",
        "GITHUB_WEBHOOK_SECRET": "",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "",
    }.items():
        monkeypatch.setenv(name, value)
