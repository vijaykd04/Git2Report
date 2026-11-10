"""Open branches = work that exists but is not merged yet. Used for the 'In progress' section."""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from git2report.models import BranchInfo


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout


def open_branches(repo: Path, since: datetime, base: str = "HEAD") -> list[BranchInfo]:
    """Branches not merged into `base` with activity since `since`. Never raises: returns [] on any problem."""
    try:
        fmt = "%(refname:short)|%(committerdate:short)|%(subject)"
        out = _git(Path(repo), "for-each-ref", f"--no-merged={base}", f"--format={fmt}", "refs/heads", "refs/remotes")
        found: dict[str, BranchInfo] = {}
        for line in out.splitlines():
            name, date, subject = line.split("|", 2)
            short = name.split("/", 1)[1] if name.startswith("origin/") else name
            if name == "origin" or short == "HEAD" or short in found or date < since.date().isoformat():
                continue
            ahead = int(_git(Path(repo), "rev-list", "--count", f"{base}..{name}").strip() or 0)
            if ahead:
                found[short] = BranchInfo(short, date, ahead, subject)
        return sorted(found.values(), key=lambda b: b.last_date, reverse=True)
    except Exception:
        return []
