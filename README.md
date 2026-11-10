# Git2Report

Turn a Git repository's history into a plain-language weekly progress report, where **every number is
counted by code** and **every line carries commit IDs as proof**. The AI (optional, local) only writes
sentences.

```
git2report --repo . --since 7d --audience guide --out report.pdf
```

## Install

```
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"          # core + pytest
pip install -e ".[ollama]"       # only if you want AI sentences (also install Ollama from ollama.com)
```

## Use

### 🖥️ Interactive Web Studio GUI
Launch the browser-based dashboard to configure, run, preview, and download reports with 1 click:
```
git2report --ui               # Opens Web Studio at http://localhost:5000
# or: git2report-ui
```

### 💻 Command Line (Terminal)
```
git2report --repo ./myproject --since 7d --all --out report.html            # PDF + Markdown + Interactive HTML
git2report --repo ./myproject --since 7d --llm gemini                       # Plain-English AI summaries (Google Gemini with Smart Cache)
git2report --repo ./myproject --since 2w --audience client --both          # PDF + Markdown for clients
git2report --repo ./myproject --llm ollama --model llama3:8b               # Local offline AI model
git2report --repo ./myproject --artifacts output/                          # also save every step's result
git2report --repo . --next "Finish saved jobs" --next "Write tests"       # add goals YOU wrote (never invented)
git2report --repo . --no-branches                                         # skip the "in progress" section
git2report --clear-cache                                                   # reset the smart summary cache
```

`--llm offline` (default) builds each sentence from the commit messages themselves.
`--llm gemini` uses Google Gemini (default `gemini-2.5-flash`) to rewrite changes in simple, everyday language understandable by anyone (pass `--api-key` or set `GEMINI_API_KEY`).
`--llm ollama` asks a local model.
If the AI is missing, returns bad JSON, or writes a number or file name, the tool retries once, then falls back to offline wording and says so in the report.

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
- Google Gemini AI integration with automatic fallback, ReportLab PDF, interactive HTML, Markdown, and 40 automated tests.
- Tried on demo repo, pallets/click, and real full-stack project (CampusThrift).

**Optional future work:** config file, multi-repo aggregator.
