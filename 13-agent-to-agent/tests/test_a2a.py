import asyncio

import httpx
from agent_to_agent.client import build_client_agent
from agent_to_agent.server import build_app, build_server_agent, exchange_rate
from crewai.a2a import A2AClientConfig
from stub_llm import StubLLM, prompt_text, tool_call

URL = "http://127.0.0.1:9999"


def rpc(app, method: str, params: dict) -> dict:
    """Call the A2A server in-process (no socket): one JSON-RPC request."""

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=URL) as client:
            response = await client.post(
                "/",
                json={"jsonrpc": "2.0", "id": "1", "method": method, "params": params},
            )
            return response.json()

    return asyncio.run(go())


def get(app, path: str) -> dict:
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=URL) as client:
            return (await client.get(path)).json()

    return asyncio.run(go())


def test_agent_card_describes_the_agent_and_its_tool():
    agent = build_server_agent(llm=StubLLM(), url=URL)

    card = get(build_app(agent, URL), "/.well-known/agent-card.json")

    assert card["name"] == "Currency desk"
    assert card["url"] == URL + "/"
    assert [skill["id"] for skill in card["skills"]] == ["exchange_rate"]


def test_server_runs_the_agent_for_an_incoming_message():
    llm = StubLLM(
        responses=[
            tool_call("exchange_rate", {"from_currency": "EUR", "to_currency": "PLN"}),
            "Final Answer: 250 EUR is 1067.50 PLN (rate 4.27).",
        ]
    )
    app = build_app(build_server_agent(llm=llm, url=URL), URL)

    reply = rpc(
        app,
        "message/send",
        {
            "message": {
                "role": "user",
                "messageId": "m1",
                "parts": [{"kind": "text", "text": "Convert 250 EUR to PLN"}],
            }
        },
    )

    assert "error" not in reply, reply
    assert "1067.50 PLN" in str(
        reply["result"]
    )  # the agent's answer came back over A2A
    assert "1 EUR = 4.27 PLN" in prompt_text(
        llm.calls[1]
    )  # the real tool ran on the server
    assert "Convert 250 EUR to PLN" in prompt_text(
        llm.calls[0]
    )  # the client's text arrived


def test_exchange_rate_tool_knows_three_pairs_and_says_so_for_others():
    assert (
        exchange_rate.run(from_currency="usd", to_currency="pln") == "1 USD = 3.91 PLN"
    )
    assert "no rate for GBP/PLN" in exchange_rate.run(
        from_currency="GBP", to_currency="PLN"
    )


def test_client_agent_points_at_the_remote_agent_card():
    endpoint = URL + "/.well-known/agent-card.json"

    agent = build_client_agent(endpoint, llm=StubLLM())

    config = agent.a2a
    assert isinstance(config, A2AClientConfig)
    assert str(config.endpoint) == endpoint and config.max_turns == 4
