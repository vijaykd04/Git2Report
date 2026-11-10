import shutil
import subprocess
from datetime import datetime, timedelta

import pytest

from git2report.models import CommitRecord, FileChange


def make_commit(message="feat(auth): add login", files=None, is_merge=False, author="Dev", date="2026-10-01", h="abc1234"):
    return CommitRecord(hash=h, message=message, date=date, author=author, is_merge=is_merge,
                        files=files if files is not None else [FileChange("routes/auth.js", 10, 2, "")])


@pytest.fixture
def commit():
    return make_commit


@pytest.fixture
def demo_repo(tmp_path):
    """A real Git repo with a feature, a fix, and the noise the tool must remove."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    repo = tmp_path / "proj"
    repo.mkdir()

    def git(*args, when=None):
        env = None
        if when:
            import os
            stamp = when.isoformat()
            env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)

    git("init", "-q", "-b", "main")
    git("config", "user.name", "Test Dev")
    git("config", "user.email", "dev@example.com")
    now = datetime.now()

    def commit_file(path, content, msg, days_ago):
        f = repo / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", msg, when=now - timedelta(days=days_ago))

    commit_file("README.md", "# demo\n", "chore: initial setup", 30)               # outside a 7-day window
    commit_file("routes/auth.js", "const a = 1;\n" * 20, "feat(auth): add login", 5)
    commit_file("package-lock.json", "x\n" * 300, "chore(deps): lock file", 4)
    commit_file("routes/auth.js", "const a = 1;\n" * 19 + "const b = 2;\n", "fix(auth): handle null user", 3)
    commit_file("README.md", "# demo!\n", "fix typo", 2)
    commit_file("components/Nav.css", ".nav { color: #fff; }\n", "style(ui): navbar colours", 1)
    # an unmerged feature branch = work in progress
    git("checkout", "-q", "-b", "feature/search")
    commit_file("routes/search.js", "// search\n", "feat(search): start search endpoint", 0)
    git("checkout", "-q", "main")
    return repo
