"""Command line: git2report --repo . --since 7d --audience guide --out report.pdf"""
from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from git2report import __version__
from git2report.models import GitReportError
from git2report.pipeline import Options, run_pipeline
from git2report.report import render_html, render_markdown, render_pdf
from git2report.summarizer import get_summarizer
from git2report.timeutil import parse_since


def _preprocess_argv(argv: list[str]) -> list[str]:
    result = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--ai":
            result.extend(["--llm", "gemini"])
            i += 1
            continue
        if arg == "--llm":
            if i + 1 < len(argv) and not argv[i + 1].startswith("-") and argv[i + 1].lower() in ("gemini", "ollama", "offline"):
                result.extend(["--llm", argv[i + 1].lower()])
                i += 2
                continue
            # When --llm is passed alone, default to gemini
            result.extend(["--llm", "gemini"])
            i += 1
            continue
        result.append(arg)
        i += 1
    return result


if len(sys.argv) > 1:
    sys.argv = [sys.argv[0]] + _preprocess_argv(sys.argv[1:])


class AppWrapper(typer.Typer):
    def __call__(self, *args, **kwargs):
        if not args and not kwargs and len(sys.argv) > 1:
            sys.argv = [sys.argv[0]] + _preprocess_argv(sys.argv[1:])
        return super().__call__(*args, **kwargs)


app = AppWrapper(add_completion=False, help="Turn Git history into a plain-language, evidence-linked progress report.")


class Audience(str, Enum):
    guide = "guide"
    client = "client"
    team = "team"


class Llm(str, Enum):
    offline = "offline"
    gemini = "gemini"
    ollama = "ollama"


def _version(value: bool):
    if value:
        typer.echo(f"git2report {__version__}")
        raise typer.Exit()


@app.command()
def main(
    repo: str = typer.Option(".", "--repo", "-r", help="Path to the Git repository or remote Git URL."),
    since: str = typer.Option("7d", "--since", "-s", help="How far back: 7d, 2w, 12h or a date like 2026-10-01."),
    audience: Audience = typer.Option(Audience.guide, "--audience", "-a", help="Who will read the report."),
    llm: Llm = typer.Option(Llm.offline, "--llm", help="'offline' uses commit messages; 'gemini' uses Google Gemini; 'ollama' uses local Ollama."),
    model: str = typer.Option("", "--model", help="AI model name (default: gemini-2.5-flash for gemini, llama3:8b for ollama)."),
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar="GEMINI_API_KEY", help="API key for Gemini (or set GEMINI_API_KEY env var)."),
    out: Path = typer.Option(Path("report.pdf"), "--out", "-o", help="Output file: .pdf, .md, or .html"),
    both: bool = typer.Option(False, "--both", help="Write both the PDF and the Markdown file."),
    html: bool = typer.Option(False, "--html", help="Write an interactive HTML report dashboard."),
    all_formats: bool = typer.Option(False, "--all", help="Write PDF, Markdown, and HTML reports."),
    planned: list[str] = typer.Option([], "--next", "-n", help="A planned goal for next period (repeat the option for several)."),
    branches: bool = typer.Option(True, "--branches/--no-branches", help="List unmerged branches as 'in progress'."),
    artifacts: Optional[Path] = typer.Option(None, "--artifacts", help="Folder to save every step's result (JSON/text)."),
    ui: bool = typer.Option(False, "--ui", help="Launch the interactive Web Studio GUI in your browser."),
    port: int = typer.Option(5000, "--port", help="Port to run the Web Studio GUI on."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable the smart summary cache."),
    clear_cache: bool = typer.Option(False, "--clear-cache", help="Clear the smart summary cache."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Hide progress messages."),
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True, help="Show version."),
):
    if clear_cache:
        from git2report.cache import default_cache
        count = default_cache.clear()
        typer.echo(f"Cleared {count} entries from smart summary cache.")
        raise typer.Exit()

    if ui:
        from git2report.web import launch_web_server
        launch_web_server(port=port)
        raise typer.Exit()

    if no_cache:
        from git2report.cache import default_cache
        default_cache.enabled = False

    log = (lambda _m: None) if quiet else (lambda m: typer.echo(m, err=True))
    try:
        raw_repo = str(repo).strip().replace("\\", "/")
        if raw_repo.startswith("https:/") and not raw_repo.startswith("https://"):
            raw_repo = "https://" + raw_repo[len("https:/"):]
        elif raw_repo.startswith("http:/") and not raw_repo.startswith("http://"):
            raw_repo = "http://" + raw_repo[len("http:/"):]

        if raw_repo.startswith(("http://", "https://", "git@")):
            repo_name = raw_repo.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            local_dir = Path("cloned_repos") / repo_name
            local_dir.parent.mkdir(parents=True, exist_ok=True)
            if not (local_dir / ".git").exists():
                log(f"Cloning remote repository {raw_repo} into {local_dir}...")
                import subprocess
                r = subprocess.run(["git", "clone", raw_repo, str(local_dir)], capture_output=True, text=True)
                if r.returncode != 0:
                    raise GitReportError(f"Failed to clone repository: {r.stderr.strip()}")
            repo_path = local_dir
        else:
            repo_path = Path(repo)

        chosen_model = model or ("gemini-2.5-flash" if llm == Llm.gemini else "llama3:8b")
        opts = Options(repo=repo_path, since=parse_since(since), audience=audience.value, artifacts=artifacts,
                       planned=planned, include_branches=branches)
        data = run_pipeline(opts, get_summarizer(llm.value, chosen_model, api_key=api_key), log=log)
        written = []
        out.parent.mkdir(parents=True, exist_ok=True)
        is_html = out.suffix.lower() == ".html"
        is_md = out.suffix.lower() == ".md"
        is_pdf = out.suffix.lower() == ".pdf" or (not is_html and not is_md)

        if all_formats or both or is_md:
            md_path = out.with_suffix(".md")
            md_path.write_text(render_markdown(data), encoding="utf-8")
            written.append(md_path)

        if all_formats or html or is_html:
            html_path = out.with_suffix(".html")
            html_path.write_text(render_html(data), encoding="utf-8")
            written.append(html_path)

        if all_formats or both or is_pdf:
            pdf_path = out if out.suffix.lower() == ".pdf" else out.with_suffix(".pdf")
            render_pdf(data, pdf_path)
            written.append(pdf_path)
    except GitReportError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    for p in written:
        typer.echo(f"Wrote {p}")
    if llm == Llm.offline:
        typer.echo("Note: offline mode used (no AI). Add --llm gemini for AI-written plain-language sentences.", err=True)


if __name__ == "__main__":
    app()
