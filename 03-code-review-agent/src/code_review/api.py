"""FastAPI service: receives GitHub pull_request webhooks, reviews in the background, posts the comment.

    uvicorn code_review.api:app --host 0.0.0.0 --port 8080

POST /review   GitHub `pull_request` event (opened / synchronize / reopened). Answers 202 at once.
POST /review/diff   {"title": "...", "diff": "..."} - synchronous review of a raw diff (for REST clients).
GET  /health
"""

import json
import logging
import os
import threading

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from code_review import github
from code_review.listeners import ReviewLogListener
from code_review.models import ReviewResult
from code_review.review import review_diff
from code_review.usage_tracker import UsageTracker

log = logging.getLogger("code_review")
app = FastAPI(title="Code review agent")

LISTENER = ReviewLogListener()
TRACKER = UsageTracker()  # totals since the service started; logged after every review
_ONE_REVIEW_AT_A_TIME = threading.Semaphore(int(os.getenv("REVIEW_CONCURRENCY", "1")))
HANDLED_ACTIONS = {"opened", "synchronize", "reopened", "ready_for_review"}


class DiffRequest(BaseModel):
    title: str = "Pull request"
    diff: str


def run_review(repo: str, number: int, title: str) -> ReviewResult:
    """Fetch the PR diff, review it, post the comment (when GITHUB_TOKEN is set), log token usage."""
    with _ONE_REVIEW_AT_A_TIME:
        diff = github.fetch_diff(repo, number)
        result = review_diff(diff, title)
        result.posted = github.post_comment(repo, number, result.comment)
        log.info(
            "reviewed %s#%s: %s findings, posted=%s",
            repo,
            number,
            len(result.findings),
            result.posted,
        )
        log.info("\n%s", TRACKER.report())
        return result


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/review", status_code=202)
async def review_webhook(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict:
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if secret and not github.verify_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=401, detail="bad signature")
    if x_github_event not in (None, "pull_request", "ping"):
        return {"status": "ignored", "reason": f"event {x_github_event}"}

    event = json.loads(body or b"{}")
    if "pull_request" not in event:
        return {"status": "ignored", "reason": "not a pull_request event"}
    if event.get("action") not in HANDLED_ACTIONS:
        return {"status": "ignored", "reason": f"action {event.get('action')}"}

    pr = event["pull_request"]
    repo = event["repository"]["full_name"]
    background.add_task(run_review, repo, pr["number"], pr.get("title", "Pull request"))
    return {"status": "accepted", "repo": repo, "pull_request": pr["number"]}


@app.post("/review/diff")
def review_raw_diff(req: DiffRequest) -> ReviewResult:
    with _ONE_REVIEW_AT_A_TIME:
        return review_diff(req.diff, req.title)
