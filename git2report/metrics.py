"""STEP 4: numbers, counted by code. The AI never produces or touches these."""
from __future__ import annotations

from git2report.config import Config
from git2report.models import CommitRecord
from git2report.rules import commit_type, is_junk, is_test


def compute_metrics(commits: list[CommitRecord], groups: dict[str, list[CommitRecord]], cfg: Config,
                    total_commits_seen: int | None = None) -> dict:
    from pathlib import Path

    files = [f for c in commits for f in c.files if not is_junk(f.path, cfg.junk)]
    test_lines = sum(f.added + f.deleted for f in files if is_test(f.path))
    code_lines = sum(f.added + f.deleted for f in files if not is_test(f.path))
    lines_added = sum(f.added for f in files)
    lines_deleted = sum(f.deleted for f in files)

    by_type: dict[str, int] = {}
    for c in commits:
        key = commit_type(c.subject) or "other"
        by_type[key] = by_type.get(key, 0) + 1
    top = max(groups, key=lambda g: (len(groups[g]), g)) if groups else ""

    author_stats: dict[str, dict] = {}
    for c in commits:
        a = c.author or "Unknown"
        if a not in author_stats:
            author_stats[a] = {"name": a, "commits": 0, "added": 0, "deleted": 0, "modules": {}}
        author_stats[a]["commits"] += 1
        for f in c.files:
            if not is_junk(f.path, cfg.junk):
                author_stats[a]["added"] += f.added
                author_stats[a]["deleted"] += f.deleted
        if c.module:
            author_stats[a]["modules"][c.module] = author_stats[a]["modules"].get(c.module, 0) + 1

    contributors = []
    for a, s in author_stats.items():
        top_mod = max(s["modules"], key=s["modules"].get) if s["modules"] else top
        contributors.append({
            "name": a,
            "commits": s["commits"],
            "added": s["added"],
            "deleted": s["deleted"],
            "lines_changed": s["added"] + s["deleted"],
            "top_module": top_mod,
        })
    contributors.sort(key=lambda x: (x["commits"], x["lines_changed"]), reverse=True)

    total_lines = max(test_lines + code_lines, 1)
    mod_lines: dict[str, int] = {}
    for mod, cs in groups.items():
        mod_files = [f for c in cs for f in c.files if not is_junk(f.path, cfg.junk)]
        mod_lines[mod] = sum(f.added + f.deleted for f in mod_files)

    module_distribution = {
        mod: round((lines / total_lines) * 100, 1)
        for mod, lines in sorted(mod_lines.items(), key=lambda kv: kv[1], reverse=True)
    }

    ext_stats: dict[str, dict] = {}
    TECH_MAP = {
        ".jsx": "React (JSX)", ".tsx": "React (TSX)", ".js": "JavaScript", ".ts": "TypeScript",
        ".py": "Python", ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".json": "JSON / Config",
        ".md": "Documentation", ".sql": "SQL / Database", ".yml": "YAML / CI", ".yaml": "YAML / CI",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".sh": "Shell Script"
    }
    for f in files:
        ext = Path(f.path).suffix.lower() or "other"
        name = TECH_MAP.get(ext, ext.upper() if ext.startswith(".") else "Other")
        if name not in ext_stats:
            ext_stats[name] = {"tech": name, "count": 0, "lines": 0}
        ext_stats[name]["count"] += 1
        ext_stats[name]["lines"] += (f.added + f.deleted)
    
    tech_stack = []
    for t, s in sorted(ext_stats.items(), key=lambda x: x[1]["lines"], reverse=True)[:5]:
        pct = round((s["lines"] / total_lines) * 100, 1)
        if pct > 0:
            tech_stack.append({"tech": t, "percentage": pct, "lines": s["lines"]})

    # Codebase Hotspots: files touched by most commits
    file_freq: dict[str, dict] = {}
    for c in commits:
        for f in c.files:
            if not is_junk(f.path, cfg.junk) and f.path:
                if f.path not in file_freq:
                    file_freq[f.path] = {"path": f.path, "commits": 0, "lines": 0}
                file_freq[f.path]["commits"] += 1
                file_freq[f.path]["lines"] += (f.added + f.deleted)
    hotspots = sorted(file_freq.values(), key=lambda x: (x["commits"], x["lines"]), reverse=True)[:5]

    return {
        "commits": len(commits),
        "commits_seen_before_filter": total_commits_seen if total_commits_seen is not None else len(commits),
        "authors": len({c.author for c in commits}),
        "lines_changed": test_lines + code_lines,                       # junk files excluded
        "lines_changed_incl_junk": sum(c.lines for c in commits),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "net_lines": lines_added - lines_deleted,
        "top_module": top,
        "modules": len(groups),
        "test_to_code_ratio": round(test_lines / max(code_lines, 1), 2),
        "commits_by_type": dict(sorted(by_type.items())),
        "contributors": contributors,
        "module_distribution": module_distribution,
        "tech_stack": tech_stack,
        "hotspots": hotspots,
    }
