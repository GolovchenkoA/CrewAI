"""GitHub: verify webhook signatures, fetch a PR diff, post the review comment."""

import hashlib
import hmac
import os

import httpx

API = "https://api.github.com"


def verify_signature(body: bytes, signature_header: str | None, secret: str) -> bool:
    """Check X-Hub-Signature-256 ("sha256=<hex hmac of the raw body>")."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _headers(accept: str) -> dict[str, str]:
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_diff(repo: str, number: int, client: httpx.Client | None = None) -> str:
    own = client is None
    client = client or httpx.Client(timeout=30)
    try:
        r = client.get(
            f"{API}/repos/{repo}/pulls/{number}",
            headers=_headers("application/vnd.github.v3.diff"),
        )
        r.raise_for_status()
        return r.text
    finally:
        if own:
            client.close()


def post_comment(
    repo: str, number: int, body: str, client: httpx.Client | None = None
) -> bool:
    """Post an issue comment on the PR. Returns False (and does nothing) without GITHUB_TOKEN."""
    if not os.getenv("GITHUB_TOKEN"):
        return False
    own = client is None
    client = client or httpx.Client(timeout=30)
    try:
        r = client.post(
            f"{API}/repos/{repo}/issues/{number}/comments",
            headers=_headers("application/vnd.github+json"),
            json={"body": body},
        )
        r.raise_for_status()
        return True
    finally:
        if own:
            client.close()
