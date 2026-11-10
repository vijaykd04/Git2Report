from git2report.config import Config
from git2report.rules import commit_type, is_junk, is_test, parse_conventional, tokens
from git2report.timeutil import parse_since
from git2report.models import GitReportError
from datetime import datetime
import pytest

CFG = Config()


def test_parse_conventional():
    assert parse_conventional("feat(auth): add login") == ("feat", "auth", "add login")
    assert parse_conventional("fix: crash") == ("fix", None, "crash")
    assert parse_conventional("update stuff") == (None, None, "update stuff")


def test_junk_matches_whole_names_only():
    assert is_junk("package-lock.json", CFG.junk)
    assert is_junk("web/package-lock.json", CFG.junk)
    assert is_junk("dist/app.js", CFG.junk)
    assert is_junk("static/app.min.js", CFG.junk)
    assert not is_junk("rebuild/engine.py", CFG.junk)       # 'build/' must not match 'rebuild/'
    assert not is_junk("src/lockfile_reader.py", CFG.junk)


def test_is_test_does_not_match_latest():
    assert is_test("tests/auth.test.js")
    assert is_test("pkg/test_models.py")
    assert is_test("src/App.spec.ts")
    assert not is_test("latest/notes.md")
    assert not is_test("src/contest.py")


def test_tokens_estimate():
    assert tokens("a" * 400) == 100


def test_parse_since():
    now = datetime(2026, 10, 14, 12, 0)
    assert parse_since("7d", now) == datetime(2026, 10, 7, 12, 0)
    assert parse_since("2w", now) == datetime(2026, 9, 30, 12, 0)
    assert parse_since("2026-10-01") == datetime(2026, 10, 1)
    with pytest.raises(GitReportError):
        parse_since("yesterday")


def test_commit_type_uses_prefix_then_first_word():
    assert commit_type("feat(auth): add login") == "feat"
    assert commit_type("Add login page") == "feat"
    assert commit_type("Fixed crash on start") == "fix"
    assert commit_type("Document completion of path") == "docs"
    assert commit_type("Remove unused code (#12)") == "refactor"
    assert commit_type("Start 8.6.0.") == "chore"
    assert commit_type("something odd") is None
