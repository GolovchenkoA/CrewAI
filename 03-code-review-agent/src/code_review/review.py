"""The review pipeline: chunk the diff, run the reviewers per chunk, merge, write the comment.

diff -> chunks (MAX_DIFF_TOKENS) -> reviewers_crew.kickoff_for_each (one run per chunk)
     -> merge + dedupe + drop findings for files that are not in the diff
     -> lead_crew (guardrail: every finding as path:line)  or the plain fallback comment
"""

import json
import logging
import os
from pathlib import Path

from code_review import observability
from code_review.crew import lead_crew, reviewers_crew
from code_review.models import Finding, ReviewFindings, ReviewResult
from code_review.tools.diff_parser import chunk_diff, parse_diff

log = logging.getLogger("code_review")

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def max_diff_tokens() -> int:
    return int(os.getenv("MAX_DIFF_TOKENS", "6000"))


def merge_findings(batches: list[list[Finding]], diff_files: set[str]) -> list[Finding]:
    """Deduplicate, drop findings about files outside the diff (hallucinations), sort by severity."""
    seen: set[tuple[str, int, str]] = set()
    merged: list[Finding] = []
    for finding in (f for batch in batches for f in batch):
        key = (finding.file, finding.line, finding.message.strip().lower())
        if finding.file not in diff_files or key in seen:
            continue
        seen.add(key)
        merged.append(finding)
    return sorted(merged, key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.line))


def render_comment(findings: list[Finding]) -> str:
    """Plain Markdown comment; used when there is nothing to merge or the lead reviewer fails."""
    if not findings:
        return "No issues found in this pull request."
    lines = [f"Automated review: {len(findings)} finding(s).", ""]
    for f in findings:
        tip = f" ({f.suggestion})" if f.suggestion else ""
        lines.append(f"- **{f.severity}** `{f.file}:{f.line}` {f.message}{tip}")
    return "\n".join(lines)


def _collect(outputs) -> list[list[Finding]]:
    batches: list[list[Finding]] = []
    for crew_output in outputs:
        for task_output in crew_output.tasks_output:
            parsed = task_output.pydantic
            if isinstance(parsed, ReviewFindings):
                batches.append(parsed.findings)
            else:
                log.warning("a reviewer returned no structured findings; skipped")
    return batches


def review_diff(
    diff: str, title: str = "Pull request", repo_root: Path | None = None
) -> ReviewResult:
    files = parse_diff(diff)
    chunks = chunk_diff(diff, max_diff_tokens())
    with observability.span(
        "review", title=title, files=len(files), chunks=len(chunks)
    ) as attrs:
        if not chunks:
            return ReviewResult(
                title=title,
                comment="The diff is empty, nothing to review.",
                findings=[],
                chunks=0,
            )

        crew = reviewers_crew(diff, repo_root)
        outputs = crew.kickoff_for_each(
            inputs=[{"title": title, "diff": c} for c in chunks]
        )
        findings = merge_findings(_collect(outputs), {f.path for f in files})

        comment = render_comment(findings)
        if findings:
            try:
                payload = json.dumps([f.model_dump() for f in findings], indent=1)
                lead = lead_crew(findings).kickoff(
                    inputs={"title": title, "findings": payload}
                )
                comment = lead.raw
            except Exception as exc:  # noqa: BLE001 - guardrail gave up or the model failed
                log.warning("lead reviewer failed (%s); posting the plain comment", exc)

        attrs["findings"] = len(findings)
        return ReviewResult(
            title=title, comment=comment, findings=findings, chunks=len(chunks)
        )
