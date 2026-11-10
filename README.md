# Git2Report

[![PyPI version](https://img.shields.io/pypi/v/git2report.svg)](https://pypi.org/project/git2report/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Turn a Git repository's history into a plain-language weekly progress report, where **every number is
counted by code** and **every line carries commit IDs as proof**. The AI (optional, local Ollama or Google Gemini) only writes
sentences.

---

## ⚡ Quick 1-Command Run (No Cloning Required!)

Anyone with Python can install and run Git2Report globally in one command:

```bash
pip install git2report
git2report --ui
```

Or run directly without installing using `pipx`:
```bash
pipx run git2report --ui
```

---

## Install for Development

```bash
git clone https://github.com/vijaykd04/Git2Report.git
cd Git2Report
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"          # includes test suite
```

## Use

### 🖥️ Interactive Web Studio GUI
Launch the browser-based dashboard to configure, run, preview, and download reports with 1 click:
```
git2report --ui               # Opens Web Studio at http://localhost:5000
# or: git2report-ui
```

### 💻 Command Line (Terminal)
```bash
# 1. Standard full-format generation (PDF + HTML + Markdown)
git2report --repo ./myproject --since 7d --all --out report.html

# 2. Local AI with Ollama (Private, offline, zero API keys)
git2report --repo ./myproject --llm ollama --model llama3:8b
# Or shortcut:
git2report --repo ./myproject --ollama --model mistral

# 3. Cloud AI with Google Gemini (Fast, smart summary caching)
git2report --repo ./myproject --llm gemini --model gemini-2.5-flash

# 4. Pure offline deterministic mode (Zero AI, instant)
git2report --repo ./myproject --llm offline --audience guide

# 5. Targeted audience personas
git2report --repo ./myproject --since 2w --audience client --both          # Business & user-facing
git2report --repo ./myproject --since 2w --audience team --both            # Engineering release notes

# 6. Sprint goals & caching
git2report --repo . --next "Finish payment gateway" --next "Write tests"   # Authentic developer goals
git2report --clear-cache                                                   # Reset summary cache
```

### AI Engines (`--llm`)
- **`--llm ollama`**: Uses a local model running on your machine via [Ollama](https://ollama.com/) (e.g., `llama3:8b`, `llama3.2`, `mistral`, `deepseek-r1:8b`, `phi4`). Zero data leaves your machine. Automatically discovers available local models. If Ollama is offline or uninstalled, it gracefully falls back to deterministic offline wording without crashing.
- **`--llm gemini`**: Uses Google Gemini (`gemini-2.5-flash`) with smart SHA-256 caching (`.git2report_cache.json`) for fast execution and zero duplicate token costs. Set `GEMINI_API_KEY` in your environment or `.env` file.
- **`--llm offline`** (default): Builds clean human sentences directly from commit messages without invoking any AI.

Every AI output is validated by code: if the model returns invalid JSON, mentions raw numbers, or mentions file paths, Git2Report automatically retries once and falls back safely.


## Evaluation (manual vs tool vs baseline)

```
git2report-eval sheet --repo ./proj --since 45d --n 25 --out eval.csv    # builds the sheet
# open eval.csv in Excel: write manual_summary, give 1-5 scores, count unsupported claims
git2report-eval score eval.csv --out results.md                          # averages: tool vs baseline
```
The baseline is what you get without the pipeline: the raw commit message (offline) or the raw commit pasted
to the AI (`--llm ollama`). Be honest in the project report about the sample size and whose repo it was.

## Audiences (offline mode)

`guide` = full list, `client` = only user-facing work (features, fixes, performance), `team` = release-notes
grouped by type. A commit's type comes from `type(scope):` if present, otherwise it is guessed from its first
word (Add = feature, Fix = fix, Remove = refactor...). It is a heuristic, so check it on your own repo.

## How it works (7 steps, one file each)

| Step | File | Output |
|---|---|---|
| 1 Extract | `extractor.py` | list of `CommitRecord` |
| 2 Filter | `filtering.py` | kept commits + a reason for every decision |
| 3 Cluster | `clustering.py` | `{module: [commits]}` (scope, then folder, then commit type) |
| 4 Metrics | `metrics.py` | numbers (junk files excluded) |
| 5 Chunk | `chunker.py` | short code text per module, within a token budget |
| 6 Summarise | `summarizer.py` | one sentence per module (AI or offline), checked by code |
| 7 Report | `report.py` | Markdown (Jinja2) and PDF (ReportLab) |

Tunable rules (junk files, noise words, aliases, budget) live in `config.py`.

## Develop

```
pytest -q                  # 38 tests, uses a throw-away real Git repo
bash scripts/make_demo_repo.sh   # 10-commit demo repo in ./demo_repo
```

## Status

Done and tested:
- Steps 1-7 deterministic pipeline with verified commit hashes.
- 🖥️ **Interactive Web Studio GUI** (`git2report --ui`) with real-time progress, live preview, and direct PDF/HTML/MD downloads.
- ⚡ **Smart Summary Cache** (`.git2report_cache.json`) for instant sub-second re-runs and 0 API token waste.
- 📊 **Visual Analytics & Charts** (Commit type distribution segmented bar & module churn chart embedded in PDF & HTML).
- Offline summaries per audience, unmerged "in progress" branches, developer-written sprint goals.
- 🦙 **Ollama Local AI & Google Gemini Cloud AI**: Choose between 100% private local models (`llama3:8b`, `mistral`, `deepseek-r1`) or Google Gemini (`gemini-2.5-flash`), with automated code-validation and fallback.
- ReportLab PDF, interactive HTML, Markdown, and 43 automated tests.
- Tried on demo repo, pallets/click, and real full-stack project (CampusThrift).

**Optional future work:** config file, multi-repo aggregator.
