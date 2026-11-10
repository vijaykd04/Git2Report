"""Git2Report: turn Git history into a plain-language, evidence-linked progress report."""
import os
import shutil
from pathlib import Path

# Prevent GitPython from crashing on import when git is missing from system PATH
os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

# Auto-detect git executable if installed in standard Windows locations
if not shutil.which("git"):
    for cand in [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        str(Path.home() / r"AppData\Local\Programs\Git\cmd\git.exe"),
        str(Path.home() / r"AppData\Local\Programs\Git\bin\git.exe"),
    ]:
        if Path(cand).exists():
            os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = cand
            os.environ["PATH"] = str(Path(cand).parent) + os.pathsep + os.environ.get("PATH", "")
            break

__version__ = "0.1.4"

