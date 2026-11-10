"""STEP 1: read commits from a Git repository into plain records."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydriller import Repository

from git2report.models import CommitRecord, FileChange, GitReportError


def extract(repo_path: Path, since: datetime) -> list[CommitRecord]:
    import shutil
    if not shutil.which("git"):
        raise GitReportError("Git is not installed on this system. Please install Git via 'winget install Git.Git' or from https://git-scm.com")
    repo_path = Path(repo_path)
    if not (repo_path / ".git").exists():
        raise GitReportError(f"'{repo_path}' is not a Git repository (no .git folder found).")
    records: list[CommitRecord] = []
    try:
        for c in Repository(str(repo_path), since=since).traverse_commits():
            records.append(CommitRecord(
                hash=c.hash[:7],
                message=c.msg.strip(),
                date=c.committer_date.date().isoformat(),
                author=c.author.name,
                is_merge=c.merge,
                files=[
                    FileChange(
                        path=f.new_path or f.old_path or "",
                        added=f.added_lines,
                        deleted=f.deleted_lines,
                        diff=f.diff or "",
                    )
                    for f in c.modified_files
                ],
            ))
    except Exception as exc:                                    # PyDriller/GitPython errors
        raise GitReportError(f"Could not read the repository: {exc}") from exc
    return records
