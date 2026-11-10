import os
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

import git2report
from git2report.cli import app

if __name__ == "__main__":
    app()

