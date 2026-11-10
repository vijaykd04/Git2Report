"""Small helpers that decide what a path or a message *is*. No Git, no AI here."""
from __future__ import annotations

import re

CONVENTIONAL = re.compile(r"^(\w+)(?:\(([^)]+)\))?!?:\s*(.+)")   # type(scope): description


def parse_conventional(subject: str) -> tuple[str | None, str | None, str]:
    """'feat(auth): add login' -> ('feat', 'auth', 'add login'); plain text -> (None, None, text)."""
    m = CONVENTIONAL.match(subject.strip())
    if not m:
        return None, None, subject.strip()
    return m.group(1).lower(), (m.group(2) or None), m.group(3).strip()


def is_junk(path: str, patterns: tuple[str, ...]) -> bool:
    p = path.replace("\\", "/")
    parts = p.split("/")
    for pat in patterns:
        if pat.endswith("/"):                       # a folder name, matched as a whole segment
            if pat[:-1] in parts[:-1]:
                return True
        elif pat.startswith("."):                   # an extension-like suffix
            if p.endswith(pat):
                return True
        elif parts[-1] == pat:                      # an exact file name
            return True
    return False


def is_test(path: str) -> bool:
    p = path.lower().replace("\\", "/")
    parts = p.split("/")
    name = parts[-1]
    return (
        any(d in ("test", "tests", "__tests__", "spec", "specs") for d in parts[:-1])
        or ".test." in name or ".spec." in name
        or name.startswith("test_") or name.endswith("_test.py")
    )


def tokens(text: str) -> int:
    """Rough token estimate: about 4 characters per token."""
    return len(text) // 4


# When a message has no 'type(scope):' prefix, guess the type from its first word. Simple and transparent.
_INFERRED = (
    ("feat", ("add", "adds", "added", "implement", "implements", "implemented", "introduce", "create", "created", "support", "build")),
    ("fix", ("fix", "fixes", "fixed", "resolve", "resolved", "correct", "handle", "patch", "prevent")),
    ("perf", ("optimize", "optimise", "speed", "cache", "faster")),
    ("refactor", ("refactor", "rename", "move", "remove", "removed", "clean", "cleanup", "split", "simplify", "deprecate",
                  "extract", "reorganize", "drop")),
    ("docs", ("document", "documents", "docs", "readme")),
    ("test", ("test", "tests")),
    ("chore", ("bump", "upgrade", "release", "start", "update", "merge")),
)


def commit_type(subject: str) -> str | None:
    """The Conventional Commit type if present; otherwise a guess from the first word; otherwise None."""
    ctype, _, desc = parse_conventional(subject)
    if ctype:
        return ctype
    words = desc.lower().split()
    first = words[0].strip("`.,:;") if words else ""
    for kind, starts in _INFERRED:
        if first in starts:
            return kind
    return None
