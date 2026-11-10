"""STEP 3: group commits by module using three rules, in this order:
1. the scope in the message, e.g. feat(auth): ...
2. the folder with the most changed lines
3. the commit type, e.g. docs: ...
Every commit also records WHY it landed in its module, so each decision can be explained."""
from __future__ import annotations

from git2report.config import Config
from git2report.models import CommitRecord
from git2report.rules import is_junk, is_test, parse_conventional


def _pretty(name: str, cfg: Config) -> str:
    key = name.strip().lower()
    if key in cfg.aliases:
        return cfg.aliases[key]
    return name.replace("-", " ").replace("_", " ").strip().title()


def _top_folder(commit: CommitRecord, cfg: Config) -> str | None:
    """Folder with the most changed lines. Test files are ignored unless the commit touched nothing else,
    otherwise a commit that changes source AND tests would be filed under 'Tests'."""
    def totals(include_tests: bool) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in commit.files:
            if is_junk(f.path, cfg.junk) or (is_test(f.path) and not include_tests):
                continue
            parts = f.path.replace("\\", "/").split("/")[:-1]          # folders only
            parts = [p for p in parts if p.lower() not in cfg.generic_folders]
            if parts:
                out[parts[0]] = out.get(parts[0], 0) + f.added + f.deleted
        return out

    t = totals(False) or totals(True)
    return max(t, key=t.get) if t else None


def module_of(commit: CommitRecord, cfg: Config) -> tuple[str, str]:
    ctype, scope, _ = parse_conventional(commit.subject)
    if scope:
        return _pretty(scope, cfg), "scope in message"
    folder = _top_folder(commit, cfg)
    if folder:
        return _pretty(folder, cfg), "top folder by lines"
    if ctype and ctype in cfg.type_modules:
        return cfg.type_modules[ctype], "commit type"
    return "Other", "fallback"


def cluster(commits: list[CommitRecord], cfg: Config) -> dict[str, list[CommitRecord]]:
    groups: dict[str, list[CommitRecord]] = {}
    for c in commits:
        c.module, c.module_reason = module_of(c, cfg)
        groups.setdefault(c.module, []).append(c)
    # Biggest modules first; ties by name so the output is stable.
    return dict(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])))
