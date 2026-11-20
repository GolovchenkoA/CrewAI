import hashlib
import hmac
import json
from pathlib import Path

import httpx
import pytest
from code_review import api, github
from code_review.models import ReviewResult
from fastapi.testclient import TestClient

EVENT = json.loads(
    (Path(__file__).parents[1] / "samples" / "pr_event.json").read_text(
        encoding="utf-8"
    )
)


@pytest.fixture
def client():
    return TestClient(api.app)


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_webhook_starts_a_background_review(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        api,
        "run_review",
        lambda repo, number, title: calls.append((repo, number, title)),
    )

    r = client.post("/review", json=EVENT, headers={"X-GitHub-Event": "pull_request"})

    assert r.status_code == 202 and r.json()["status"] == "accepted"
    assert calls == [("your-org/your-repo", 7, "Add user lookup")]


def test_webhook_ignores_other_actions_and_events(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, "run_review", lambda *a: calls.append(a))

    closed = client.post("/review", json={**EVENT, "action": "closed"})
    push = client.post("/review", json=EVENT, headers={"X-GitHub-Event": "push"})

    assert closed.json()["status"] == "ignored" and push.json()["status"] == "ignored"
    assert calls == []


def test_webhook_checks_the_signature_when_a_secret_is_set(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setattr(api, "run_review", lambda *a: None)
    body = json.dumps(EVENT).encode()
    headers = {"Content-Type": "application/json"}

    assert client.post("/review", content=body, headers=headers).status_code == 401
    bad = {**headers, "X-Hub-Signature-256": sign(body, "wrong")}
    assert client.post("/review", content=body, headers=bad).status_code == 401
    good = {**headers, "X-Hub-Signature-256": sign(body, "s3cret")}
    assert client.post("/review", content=body, headers=good).status_code == 202


def test_review_diff_endpoint(client, monkeypatch):
    fake = ReviewResult(title="t", comment="ok", findings=[], chunks=1)
    monkeypatch.setattr(api, "review_diff", lambda diff, title: fake)

    r = client.post("/review/diff", json={"title": "t", "diff": "x"})

    assert r.status_code == 200 and r.json()["comment"] == "ok"


def test_run_review_fetches_reviews_and_posts(monkeypatch):
    monkeypatch.setattr(api.github, "fetch_diff", lambda repo, n: "DIFF")
    monkeypatch.setattr(
        api,
        "review_diff",
        lambda diff, title: ReviewResult(
            title=title, comment="c", findings=[], chunks=1
        ),
    )
    posted = []
    monkeypatch.setattr(
        api.github,
        "post_comment",
        lambda repo, n, body: posted.append((repo, n, body)) or True,
    )

    result = api.run_review("o/r", 3, "T")

    assert result.posted is True and posted == [("o/r", 3, "c")]


def test_github_client_without_token_does_not_post(monkeypatch):
    assert github.post_comment("o/r", 1, "x") is False


def test_github_client_calls(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t0k")
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(
            (
                request.method,
                request.url.path,
                request.headers["authorization"],
                request.headers["accept"],
            )
        )
        return (
            httpx.Response(200, text="diff text", json=None)
            if request.method == "GET"
            else httpx.Response(201, json={})
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    assert github.fetch_diff("o/r", 5, client) == "diff text"
    assert github.post_comment("o/r", 5, "hello", client) is True
    assert seen[0][:2] == ("GET", "/repos/o/r/pulls/5") and "v3.diff" in seen[0][3]
    assert seen[1][:2] == ("POST", "/repos/o/r/issues/5/comments")
    assert all(s[2] == "Bearer t0k" for s in seen)
