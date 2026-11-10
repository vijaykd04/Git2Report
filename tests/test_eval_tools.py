import csv

from typer.testing import CliRunner

from git2report.eval_tools import COLUMNS, app, pick_evenly, summarize_scores

runner = CliRunner()


def test_pick_evenly_is_deterministic_and_spread():
    items = list(range(100))
    assert pick_evenly(items, 5) == [0, 20, 40, 60, 80]
    assert pick_evenly(items, 5) == pick_evenly(items, 5)
    assert pick_evenly([1, 2], 10) == [1, 2]


def test_sheet_then_score_round_trip(demo_repo, tmp_path):
    out = tmp_path / "eval.csv"
    r = runner.invoke(app, ["sheet", "--repo", str(demo_repo), "--since", "7d", "--n", "3", "--out", str(out)])
    assert r.exit_code == 0, r.output
    rows = list(csv.DictReader(open(out, encoding="utf-8-sig")))
    assert len(rows) == 3 and list(rows[0].keys()) == COLUMNS
    assert rows[0]["tool_sentence"] and rows[0]["baseline_sentence"] == rows[0]["message"]    # offline baseline = raw message
    for i, row in enumerate(rows):                                  # simulate the human filling it in
        row.update(tool_accuracy_1to5="4", tool_readability_1to5="5", tool_unsupported_claims="0",
                   baseline_accuracy_1to5="3", baseline_readability_1to5="2", baseline_unsupported_claims=str(i))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(rows)
    r = runner.invoke(app, ["score", str(out)])
    assert r.exit_code == 0 and "4.00 (n=3)" in r.output and "5.00 (n=3)" in r.output
    assert "3 over 3 rows" in r.output                              # baseline unsupported: 0+1+2


def test_score_ignores_blank_and_text_cells():
    rows = [{"tool_accuracy_1to5": "5"}, {"tool_accuracy_1to5": ""}, {"tool_accuracy_1to5": "n/a"}, {"tool_accuracy_1to5": "3"}]
    assert "4.00 (n=2)" in summarize_scores(rows)
