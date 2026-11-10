"""Evaluation helpers: make a sheet to fill in by hand, then score it.

    git2report-eval sheet --repo ./proj --since 45d --n 25 --out eval.csv
    (fill in the empty columns in Excel: manual summary + 1-5 scores)
    git2report-eval score eval.csv

Per sampled commit the sheet holds: the TOOL sentence (our pipeline) and a BASELINE sentence
(what you get by pasting the raw commit to an AI with no pipeline; offline mode: the raw commit message)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

import typer

from git2report.chunker import chunk_module
from git2report.clustering import cluster
from git2report.config import Config
from git2report.extractor import extract
from git2report.filtering import filter_commits
from git2report.models import GitReportError
from git2report.summarizer import SummaryRequest, get_summarizer
from git2report.timeutil import parse_since

app = typer.Typer(add_completion=False, help="Build and score the manual-vs-tool evaluation sheet.")

COLUMNS = ["hash", "message", "module", "tool_sentence", "tool_mode", "baseline_sentence",
           "manual_summary", "tool_accuracy_1to5", "tool_readability_1to5", "tool_unsupported_claims",
           "baseline_accuracy_1to5", "baseline_readability_1to5", "baseline_unsupported_claims", "notes"]


def pick_evenly(items: list, n: int) -> list:
    """Deterministic, evenly spread sample (so the sheet can be rebuilt identically)."""
    if n >= len(items):
        return list(items)
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def baseline_sentence(commit, summarizer) -> str:
    if hasattr(summarizer, "ask"):
        diff = "\n".join(f.diff for f in commit.files)[:1500]
        prompt = f"Explain this git commit to a non-technical person.\nMessage: {commit.subject}\nChanges:\n{diff}"
        try:
            return " ".join(summarizer.ask(prompt).split())
        except Exception as exc:
            return f"[AI unavailable: {type(exc).__name__}] {commit.subject}"
    return commit.subject                                   # offline baseline = the raw commit message


@app.command()
def sheet(
    repo: Path = typer.Option(Path("."), "--repo", "-r"),
    since: str = typer.Option("45d", "--since", "-s"),
    n: int = typer.Option(25, "--n", help="How many commits to sample."),
    audience: str = typer.Option("guide", "--audience", "-a"),
    llm: str = typer.Option("offline", "--llm", help="offline or ollama"),
    model: str = typer.Option("llama3:8b", "--model"),
    out: Path = typer.Option(Path("eval.csv"), "--out", "-o"),
):
    cfg = Config()
    try:
        commits = extract(repo, parse_since(since))
        kept, _ = filter_commits(commits, cfg)
        if not kept:
            raise GitReportError("No usable commits in that window; try a longer --since.")
        cluster(kept, cfg)
    except GitReportError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    summarizer = get_summarizer(llm, model)
    rows = []
    for c in pick_evenly(kept, n):
        res = summarizer.summarize(SummaryRequest(c.module, [c], chunk_module([c], cfg).text, audience))
        rows.append({"hash": c.hash, "message": c.subject, "module": c.module, "tool_sentence": res.text,
                     "tool_mode": res.mode, "baseline_sentence": baseline_sentence(c, summarizer)})
    with open(out, "w", newline="", encoding="utf-8-sig") as f:         # utf-8-sig so Excel opens it correctly
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    typer.echo(f"Wrote {out} with {len(rows)} commits. Fill in the empty columns, then run: git2report-eval score {out}")


def _nums(rows: list[dict], col: str) -> list[float]:
    out = []
    for r in rows:
        try:
            out.append(float((r.get(col) or "").strip()))
        except ValueError:
            continue
    return out


def _avg(xs: list[float]) -> str:
    return f"{sum(xs) / len(xs):.2f}" if xs else "n/a"


def summarize_scores(rows: list[dict]) -> str:
    lines = ["| Measure | Tool (our pipeline) | Baseline |", "|---|---|---|"]
    for label, t, b in (("Accuracy (1-5, higher is better)", "tool_accuracy_1to5", "baseline_accuracy_1to5"),
                        ("Readability (1-5, higher is better)", "tool_readability_1to5", "baseline_readability_1to5")):
        tv, bv = _nums(rows, t), _nums(rows, b)
        lines.append(f"| {label} | {_avg(tv)} (n={len(tv)}) | {_avg(bv)} (n={len(bv)}) |")
    tu, bu = _nums(rows, "tool_unsupported_claims"), _nums(rows, "baseline_unsupported_claims")
    lines.append(f"| Unsupported claims (total, lower is better) | {int(sum(tu))} over {len(tu)} rows | {int(sum(bu))} over {len(bu)} rows |")
    return "\n".join(lines)


@app.command()
def score(sheet_path: Path = typer.Argument(..., help="The filled-in CSV"),
          out: Optional[Path] = typer.Option(None, "--out", "-o", help="Also save the table as Markdown")):
    with open(sheet_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    table = summarize_scores(rows)
    typer.echo(f"{len(rows)} rows read\n\n{table}")
    if out:
        out.write_text(table + "\n", encoding="utf-8")


if __name__ == "__main__":
    app()
