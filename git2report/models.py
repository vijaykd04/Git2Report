"""Plain data containers shared by every pipeline step."""
from __future__ import annotations

from dataclasses import dataclass, field


class GitReportError(Exception):
    """A problem the user can fix (bad path, no commits, ...). Shown without a traceback."""


@dataclass
class FileChange:
    path: str
    added: int
    deleted: int
    diff: str = ""


@dataclass
class CommitRecord:
    hash: str
    message: str
    date: str
    author: str
    is_merge: bool
    files: list[FileChange] = field(default_factory=list)
    module: str = ""
    module_reason: str = ""

    @property
    def subject(self) -> str:
        text = self.message.strip()
        return text.splitlines()[0] if text else ""

    @property
    def lines(self) -> int:
        return sum(f.added + f.deleted for f in self.files)


@dataclass
class BranchInfo:
    name: str
    last_date: str
    ahead: int          # commits on the branch that are not yet in the current branch
    subject: str
