from pathlib import Path

import pytest
from triage_flow import mcp_server

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(autouse=True)
def data_dir(monkeypatch):
    monkeypatch.setenv("TRIAGE_DATA_DIR", str(DATA))


def test_get_customer():
    assert mcp_server.get_customer("C-100")["plan"] == "pro"
    assert "error" in mcp_server.get_customer("C-999")


def test_search_orders_newest_first_and_status_filter():
    orders = mcp_server.search_orders("C-100")
    assert [o["order_id"] for o in orders][:1] in (
        ["O-1002"],
        ["O-1003"],
    )  # both 2026-11-01
    assert len(orders) == 3
    assert (
        mcp_server.search_orders("C-300", status="refunded")[0]["order_id"] == "O-3001"
    )
    assert mcp_server.search_orders("C-300", status="pending") == []


def test_get_ticket():
    assert mcp_server.get_ticket("T-1002")["customer_id"] == "C-300"
    assert "error" in mcp_server.get_ticket("T-0")


def test_tools_are_registered():
    import asyncio

    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert names == {"get_ticket", "get_customer", "search_orders"}
