"""STEP 2: drop commits a reader does not care about (merges, typos, unfinished work)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from git2report.config import Config
from git2report.models import CommitRecord


@dataclass
class Decision:
    hash: str
    subject: str
    kept: bool
    reason: str


def decide(commit: CommitRecord, cfg: Config) -> Decision:
    subject = commit.subject
    if commit.is_merge or subject.lower().startswith("merge "):
        return Decision(commit.hash, subject, False, "merge commit")
    words = "|".join(re.escape(w) for w in cfg.noise_words)
    if re.search(rf"\b({words})\b", subject.lower()):
        if commit.lines >= cfg.keep_if_lines:
            return Decision(commit.hash, subject, True, "noise word, but big change: kept")
        return Decision(commit.hash, subject, False, "noise word and small change")
    return Decision(commit.hash, subject, True, "ok")


def filter_commits(commits: list[CommitRecord], cfg: Config) -> tuple[list[CommitRecord], list[Decision]]:
    decisions = [decide(c, cfg) for c in commits]
    kept = [c for c, d in zip(commits, decisions) if d.kept]
    return kept, decisions
