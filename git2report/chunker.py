"""STEP 5: shrink a module's code changes to fit the AI's limit.
Drop junk files, rank files (source before tests, big before small), split into hunks,
keep only the added/removed lines, and stop when the token budget is full."""
from __future__ import annotations

import re
from dataclasses import dataclass

from git2report.config import Config
from git2report.models import CommitRecord
from git2report.rules import is_junk, is_test, tokens


@dataclass
class Chunk:
    text: str
    raw_tokens: int
    used_tokens: int
    hunks_dropped: int


def chunk_module(commits: list[CommitRecord], cfg: Config, budget: int | None = None) -> Chunk:
    budget = cfg.token_budget if budget is None else budget
    all_files = [f for c in commits for f in c.files]
    raw = sum(tokens(f.diff) for f in all_files)
    files = [f for f in all_files if not is_junk(f.path, cfg.junk) and f.diff.strip()]
    files.sort(key=lambda f: (is_test(f.path), -(f.added + f.deleted)))
    parts: list[str] = []
    used = dropped = 0
    for f in files:
        for hunk in re.split(r"(?m)^(?=@@)", f.diff):
            if not hunk.strip():
                continue
            body = "\n".join(
                line for line in hunk.splitlines()
                if line[:1] in ("+", "-") and not line.startswith(("+++", "---"))
            )
            if not body.strip():
                continue
            piece = f"# {f.path}\n{body}"
            cost = tokens(piece)
            if used + cost <= budget:
                parts.append(piece)
                used += cost
            else:
                dropped += 1
    return Chunk("\n".join(parts), raw, used, dropped)
