import json

from typer.testing import CliRunner

from git2report.cli import app

runner = CliRunner()


def test_cli_writes_pdf_markdown_and_artifacts(demo_repo, tmp_path):
    out = tmp_path / "report.pdf"
    art = tmp_path / "art"
    result = runner.invoke(app, ["--repo", str(demo_repo), "--since", "7d", "--out", str(out), "--both",
                                 "--artifacts", str(art), "--quiet"])
    assert result.exit_code == 0, result.output
    assert out.read_bytes()[:4] == b"%PDF"
    md = out.with_suffix(".md").read_text(encoding="utf-8")
    assert "Authentication" in md and "UI" in md
    assert "Evidence:" in md and "fix typo" not in md                    # noise never reaches the report
    metrics = json.loads((art / "metrics.json").read_text())
    assert metrics["commits_seen_before_filter"] == 5                    # 6 commits, 1 older than 7 days
    assert metrics["commits"] == 4
    assert metrics["lines_changed_incl_junk"] - metrics["lines_changed"] >= 300     # lock file not counted
    clusters = json.loads((art / "clusters.json").read_text())
    assert len(clusters["Authentication"]) == 2
    assert (art / "prompts").exists() and (art / "chunks").exists()
    assert "offline" in md.lower()                                       # the report says no AI was used


def test_evidence_hashes_come_from_git_not_from_text(demo_repo, tmp_path):
    out = tmp_path / "r.md"
    runner.invoke(app, ["--repo", str(demo_repo), "--out", str(out), "-q"])
    import subprocess
    log = subprocess.run(["git", "log", "--format=%h"], cwd=demo_repo, capture_output=True, text=True).stdout.split()
    md = out.read_text(encoding="utf-8")
    import re
    hashes = re.findall(r"Evidence: ([0-9a-f, ]+)", md)
    assert hashes and all(h.strip() in log for line in hashes for h in line.split(","))


def test_friendly_errors(tmp_path, demo_repo):
    r = runner.invoke(app, ["--repo", str(tmp_path / "nope"), "--out", str(tmp_path / "x.md")])
    assert r.exit_code == 1 and "not a Git repository" in r.output
    r = runner.invoke(app, ["--repo", str(demo_repo), "--since", "banana", "--out", str(tmp_path / "x.md")])
    assert r.exit_code == 1 and "Cannot understand --since" in r.output
    r = runner.invoke(app, ["--repo", str(demo_repo), "--since", "1h", "--out", str(tmp_path / "x.md")])
    assert r.exit_code == 1 and "No commits found" in r.output


def test_in_progress_planned_and_glance_sections(demo_repo, tmp_path):
    out = tmp_path / "r.md"
    r = runner.invoke(app, ["--repo", str(demo_repo), "--out", str(out), "-q",
                            "--next", "Finish search endpoint", "-n", "Write evaluation set"])
    assert r.exit_code == 0, r.output
    md = out.read_text(encoding="utf-8")
    assert "## In progress (open branches)" in md and "`feature/search`" in md
    assert "## Planned goals (written by the developer)" in md and "- Finish search endpoint" in md
    assert "**At a glance:** 1 feature, 2 fixes" not in md           # fix typo is filtered, so 1 fix
    assert "**At a glance:**" in md and "feature" in md
    out2 = tmp_path / "r2.md"
    runner.invoke(app, ["--repo", str(demo_repo), "--out", str(out2), "-q", "--no-branches"])
    assert "In progress" not in out2.read_text(encoding="utf-8")
    assert "Planned goals" not in out2.read_text(encoding="utf-8")      # never invented


def test_audience_changes_report_in_offline_mode(demo_repo, tmp_path):
    texts = {}
    for aud in ("guide", "client", "team"):
        out = tmp_path / f"{aud}.md"
        runner.invoke(app, ["--repo", str(demo_repo), "--audience", aud, "--out", str(out), "-q"])
        texts[aud] = out.read_text(encoding="utf-8")
    assert len(set(texts.values())) == 3
    assert "Work completed:" in texts["guide"] and "What is new or improved:" in texts["client"] and "Added:" in texts["team"]
