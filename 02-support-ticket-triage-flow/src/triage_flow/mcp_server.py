"""MCP server (FastMCP, stdio) that exposes ticket, customer and order data to the specialist agents.

Run by the flow as a child process: `python -m triage_flow.mcp_server`.
Data comes from TRIAGE_DATA_DIR (default: <project>/data).
"""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ticket-data")


def data_dir() -> Path:
    default = Path(__file__).resolve().parents[2] / "data"
    return Path(os.getenv("TRIAGE_DATA_DIR") or default)


def _load(name: str) -> list[dict]:
    return json.loads((data_dir() / name).read_text(encoding="utf-8"))


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Return a support ticket (subject, body, customer_id) by ticket id, e.g. 'T-1001'."""
    for path in sorted((data_dir() / "tickets").glob("*.json")):
        ticket = json.loads(path.read_text(encoding="utf-8"))
        if ticket["ticket_id"] == ticket_id:
            return ticket
    return {"error": f"ticket {ticket_id} not found"}


@mcp.tool()
def get_customer(customer_id: str) -> dict:
    """Return the customer profile (name, plan, email, customer since) by customer id, e.g. 'C-100'."""
    for customer in _load("customers.json"):
        if customer["customer_id"] == customer_id:
            return customer
    return {"error": f"customer {customer_id} not found"}


@mcp.tool()
def search_orders(customer_id: str, status: str = "") -> list[dict]:
    """List a customer's orders/charges, newest first. Optional status filter: paid, refunded, pending."""
    orders = [o for o in _load("orders.json") if o["customer_id"] == customer_id]
    if status:
        orders = [o for o in orders if o["status"] == status]
    return sorted(orders, key=lambda o: o["date"], reverse=True)


if __name__ == "__main__":
    mcp.run()
