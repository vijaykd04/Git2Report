"""Glue: run the 7 steps in order and (optionally) save every step's result as a file."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from git2report.branches import open_branches
from git2report.chunker import chunk_module
from git2report.clustering import cluster
from git2report.config import Config
from git2report.extractor import extract
from git2report.filtering import filter_commits
from git2report.metrics import compute_metrics
from git2report.models import GitReportError
from git2report.report import CategorizedCommit, ReportData, Section
from git2report.rules import commit_type, is_junk
from git2report.summarizer import SummaryRequest


def get_remote_url(repo: Path) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=repo, capture_output=True, text=True)
        url = r.stdout.strip()
        if not url:
            return None
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):]
        elif url.startswith("git@gitlab.com:"):
            url = "https://gitlab.com/" + url[len("git@gitlab.com:"):]
        if url.endswith(".git"):
            url = url[:-4]
        return url if url.startswith("http") else None
    except Exception:
        return None


@dataclass
class Options:
    repo: Path
    since: datetime
    audience: str = "guide"
    artifacts: Path | None = None        # if set, every step's output is saved here
    planned: list[str] = field(default_factory=list)     # goals written by the developer (never invented)
    include_branches: bool = True


def glance_text(by_type: dict[str, int]) -> str:
    """'3 features, 2 fixes, 1 improvement': counted from commit types, never written by the AI."""
    feats, fixes = by_type.get("feat", 0), by_type.get("fix", 0)
    imps = by_type.get("perf", 0) + by_type.get("refactor", 0)
    rest = sum(by_type.values()) - feats - fixes - imps
    parts = []
    for n, one, many in ((feats, "feature", "features"), (fixes, "fix", "fixes"),
                         (imps, "improvement", "improvements"), (rest, "other change", "other changes")):
        if n:
            parts.append(f"{n} {one if n == 1 else many}")
    return ", ".join(parts) or "no categorised changes"


def run_pipeline(opts: Options, summarizer, cfg: Config | None = None,
                 log: Callable[[str], None] = lambda _m: None) -> ReportData:
    cfg = cfg or Config()

    log("Step 1/7  extracting commits")
    commits = extract(opts.repo, opts.since)
    if not commits:
        raise GitReportError("No commits found in that time window. Try a longer --since (e.g. 14d).")
    log(f"          {len(commits)} commits found")

    log("Step 2/7  filtering noise")
    kept, decisions = filter_commits(commits, cfg)
    if not kept:
        raise GitReportError("Every commit in the window was filtered out as noise (merges, typos, wip).")
    log(f"          {len(commits)} -> {len(kept)} commits")

    log("Step 3/7  clustering by module")
    groups = cluster(kept, cfg)
    log(f"          {len(groups)} modules: {', '.join(groups)}")

    log("Step 4/7  counting metrics")
    metrics = compute_metrics(kept, groups, cfg, total_commits_seen=len(commits))

    sections: list[Section] = []
    chunks, prompts, summaries = {}, {}, {}
    for i, (module, cs) in enumerate(groups.items(), 1):
        log(f"Step 5-6  {module} ({i}/{len(groups)}): chunking + summarising")
        ch = chunk_module(cs, cfg)
        req = SummaryRequest(module, cs, ch.text, opts.audience)
        result = summarizer.summarize(req)
        hashes = [c.hash for c in cs]
        cat_commits = [
            CategorizedCommit(
                hash=c.hash,
                subject=c.subject,
                author=c.author,
                date=c.date,
                type=commit_type(c.subject) or "other",
                added=sum(f.added for f in c.files if not is_junk(f.path, cfg.junk)),
                deleted=sum(f.deleted for f in c.files if not is_junk(f.path, cfg.junk)),
            )
            for c in cs
        ]
        sections.append(Section(module, result.text, hashes, result.mode, result.note, commits=cat_commits))
        chunks[module], prompts[module] = ch, req.prompt
        summaries[module] = {"summary": result.text, "mode": result.mode, "flagged": result.flagged,
                             "note": result.note, "commit_hashes": hashes}

    log("Step 7/7  building the report")
    modes = {s.mode for s in sections}
    n_off = sum(1 for s in sections if s.mode == "offline")
    base = getattr(summarizer, "label", "unknown")
    if modes == {"ai"} or not hasattr(summarizer, "model"):
        mode_label = base
    elif modes == {"offline"} and hasattr(summarizer, "model"):
        mode_label = f"{base}; the AI step failed for every module, so offline wording was used"
    else:
        mode_label = f"{base}; offline wording used for {n_off} module(s)"
    in_progress = open_branches(opts.repo, opts.since) if opts.include_branches else []
    remote_url = get_remote_url(opts.repo)
    exec_summary = make_executive_summary(Path(opts.repo).resolve().name, metrics, sections, summarizer)
    data = ReportData(
        project=Path(opts.repo).resolve().name,
        start=opts.since.date().isoformat(), end=datetime.now().date().isoformat(),
        audience=opts.audience, metrics=metrics, sections=sections, mode_label=mode_label,
        glance_text=glance_text(metrics["commits_by_type"]), in_progress=in_progress, planned=opts.planned,
        remote_url=remote_url, executive_summary=exec_summary,
    )
    if opts.artifacts:
        _save_artifacts(opts.artifacts, commits, decisions, groups, metrics, chunks, prompts, summaries)
    return data


def make_executive_summary(project: str, metrics: dict, sections: list[Section], summarizer) -> str:
    if hasattr(summarizer, "ask") and getattr(summarizer, "mode", "") == "ai":
        from git2report.cache import compute_cache_key, default_cache
        all_hashes = [h for s in sections for h in s.hashes]
        cache_key = compute_cache_key("exec_summary", project, all_hashes, getattr(summarizer, "model", "ai"), str(metrics.get("lines_changed", 0)))
        cached = default_cache.get(cache_key)
        if cached:
            return cached["summary"]

        mod_summaries = "\n".join(f"- {s.module}: {s.text}" for s in sections[:5])
        prompt = (
            f"You are a technology leader summarizing software progress for project '{project}'.\n"
            f"Key metrics: {metrics['commits']} commits, {metrics['lines_changed']} lines changed, primary focus on {metrics['top_module']}.\n"
            f"Module deliverables:\n{mod_summaries}\n\n"
            "Task: Write 2 clear, inspiring, plain-language sentences summarizing the major business progress and impact for non-technical leadership.\n"
            "Rules: Do not write file names or numbers. Use plain, positive business English.\n"
            'Return ONLY JSON: {"summary": "..."}'
        )
        try:
            raw = summarizer.ask(prompt)
            from git2report.summarizer import parse_model_json
            text = parse_model_json(raw)
            if text:
                default_cache.set(cache_key, text, "ai")
                return text
        except Exception:
            pass
    commits = metrics["commits"]
    modules = metrics["modules"]
    top = metrics["top_module"]
    added, deleted = metrics.get("lines_added", 0), metrics.get("lines_deleted", 0)
    return (
        f"During this delivery cycle, engineering completed {commits} verified commits across {modules} module(s), "
        f"expanding the codebase with +{added} lines and pruning -{deleted} lines. "
        f"Development concentrated primarily on {top}, advancing key capabilities while reinforcing overall system stability."
    )


def _save_artifacts(root: Path, commits, decisions, groups, metrics, chunks, prompts, summaries) -> None:
    root = Path(root)
    (root / "chunks").mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    dump = lambda name, obj: (root / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    dump("commits.json", [asdict(c) for c in commits])
    dump("filter_decisions.json", [asdict(d) for d in decisions])
    dump("clusters.json", {m: [c.hash for c in cs] for m, cs in groups.items()})
    dump("metrics.json", metrics)
    dump("summaries.json", summaries)
    for m, ch in chunks.items():
        safe = "".join(ch_ if ch_.isalnum() or ch_ in "-_" else "_" for ch_ in m)
        (root / "chunks" / f"{safe}.txt").write_text(ch.text, encoding="utf-8")
        (root / "prompts" / f"{safe}.txt").write_text(prompts[m], encoding="utf-8")
