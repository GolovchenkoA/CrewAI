"""Parse a unified git diff into files and hunks, and split it into chunks that fit a context window."""

import re
from dataclasses import dataclass, field

_FILE_RE = re.compile(r"^diff --git a/(?P<old>\S+) b/(?P<new>\S+)$")
_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,\d+)? @@")


def estimate_tokens(text: str) -> int:
    """Rough size: 1 token is about 4 characters. Good enough for splitting."""
    return len(text) // 4 + 1


@dataclass
class FileDiff:
    path: str
    header: str  # "diff --git", "index", "---", "+++" lines
    hunks: list[str] = field(default_factory=list)
    added: int = 0
    removed: int = 0

    @property
    def is_test(self) -> bool:
        p = f"/{self.path.lower()}"
        return "test" in p.split("/")[-1] or "/tests/" in p or "/test/" in p


def parse_diff(diff: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    hunk: list[str] = []

    def close_hunk() -> None:
        if current is not None and hunk:
            current.hunks.append("".join(hunk))
        hunk.clear()

    for line in diff.splitlines(keepends=True):
        m = _FILE_RE.match(line.rstrip("\r\n"))
        if m:
            close_hunk()
            current = FileDiff(path=m["new"], header=line)
            files.append(current)
        elif current is None:
            continue
        elif _HUNK_RE.match(line):
            close_hunk()
            hunk.append(line)
        elif hunk:
            hunk.append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current.added += 1
            elif line.startswith("-") and not line.startswith("---"):
                current.removed += 1
        else:
            current.header += (
                line  # index / --- / +++ / mode lines (also binary or rename notes)
            )
    close_hunk()
    return files


def number_new_lines(hunk: str) -> str:
    """Prefix each line of a hunk with its line number in the new file, so the model can cite it."""
    out: list[str] = []
    new_line = 0
    for line in hunk.splitlines():
        m = _HUNK_RE.match(line)
        if m:
            new_line = int(m["start"])
            out.append(line)
        elif line.startswith("-"):
            out.append(f"     {line}")
        else:
            out.append(f"{new_line:>4} {line}")
            new_line += 1
    return "\n".join(out) + "\n"


def chunk_diff(diff: str, max_tokens: int) -> list[str]:
    """Split a diff into pieces of about `max_tokens`, keeping files together when they fit.

    A file that alone exceeds the limit is split by hunks, with its header repeated in each piece.
    Lines are numbered with their NEW line numbers.
    """
    pieces: list[str] = []
    current = ""
    for f in parse_diff(diff):
        numbered = [number_new_lines(h) for h in f.hunks]
        file_text = f.header + "".join(numbered)
        if estimate_tokens(file_text) <= max_tokens:
            units = [file_text]
        else:  # too big: one unit per hunk, each with the file header
            units = [f.header + h for h in numbered]
        for unit in units:
            if current and estimate_tokens(current + unit) > max_tokens:
                pieces.append(current)
                current = ""
            current += unit
    if current.strip():
        pieces.append(current)
    return pieces
