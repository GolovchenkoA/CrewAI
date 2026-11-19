import os
import socket
from pathlib import Path

# Must be set before crewai / triage_flow are imported: SQLite, memory files and the flow DB go here.
_STORE = Path(__file__).parent / ".crewai-test-storage"
os.environ["CREWAI_STORAGE_DIR"] = str(_STORE)
os.environ["FLOW_DB"] = str(_STORE / "flow_states.db")

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
    monkeypatch.chdir(tmp_path)  # output/ lands in a temp dir
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    for name, value in {
        "LLM_PROVIDER": "local",
        "USE_MCP": "false",
        "USE_MEMORY": "false",
        "USE_KNOWLEDGE": "false",
        "HITL_MODE": "auto",
        "VERBOSE": "false",
        "CONFIDENCE_THRESHOLD": "0.7",
    }.items():
        monkeypatch.setenv(name, value)
