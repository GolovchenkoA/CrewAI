"""Custom tools for the reviewers: a repo file reader and a changed-files summary."""

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from code_review.tools.diff_parser import parse_diff

MAX_FILE_CHARS = 8000


class _PathArgs(BaseModel):
    path: str = Field(
        description="File path relative to the repository root, e.g. src/app/service.py"
    )


class _NoArgs(BaseModel):
    pass


class RepoFileTool(BaseTool):
    """Read a file of the checked-out repository (read-only, cannot leave the repository root)."""

    name: str = "read_repo_file"
    description: str = (
        "Read a source file from the repository under review, to see the code around a change "
        "or to check whether a test file exists. Input: a path relative to the repository root."
    )
    args_schema: type[BaseModel] = _PathArgs
    root: Path

    def _run(self, path: str) -> str:
        base = self.root.resolve()
        target = (base / path).resolve()
        if base != target and base not in target.parents:
            return "Error: path is outside the repository."
        if not target.is_file():
            return f"Error: {path} does not exist."
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n... [truncated]"
        return text


class DiffSummaryTool(BaseTool):
    """List the files of the whole pull request with added/removed line counts."""

    name: str = "list_changed_files"
    description: str = (
        "List every file changed by the pull request with its added and removed line counts "
        "and whether it is a test file. Use it to check whether changed code has matching tests."
    )
    args_schema: type[BaseModel] = _NoArgs
    diff: str

    def _run(self) -> str:
        rows = [
            f"{f.path}  +{f.added} -{f.removed}  {'TEST' if f.is_test else 'code'}"
            for f in parse_diff(self.diff)
        ]
        return "\n".join(rows) or "The diff is empty."
