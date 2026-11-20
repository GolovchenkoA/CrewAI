"""Structured outputs: what a reviewer returns and what the service reports."""

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]


class Finding(BaseModel):
    file: str = Field(description="Path of the changed file, as in the diff")
    line: int = Field(ge=1, description="Line number in the NEW version of the file")
    severity: Severity
    message: str = Field(description="What is wrong, in one or two sentences")
    suggestion: str = Field(default="", description="How to fix it")


class ReviewFindings(BaseModel):
    """Output of one reviewer for one diff chunk."""

    findings: list[Finding] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """What the service returns for one pull request or diff."""

    title: str
    comment: str  # Markdown, ready to post
    findings: list[Finding]
    chunks: int
    posted: bool = False
