from git2report.chunker import chunk_module
from git2report.config import Config
from git2report.models import FileChange
from git2report.rules import tokens

CFG = Config()
DIFF = "@@ -1,2 +1,2 @@ ctx\n-old line\n+new line\n context\n"


def test_junk_is_dropped_and_only_changed_lines_kept(commit):
    c = commit(files=[FileChange("package-lock.json", 400, 0, "@@ -0,0 +1 @@\n+" + "x" * 4000),
                      FileChange("routes/a.js", 1, 1, DIFF)])
    ch = chunk_module([c], CFG)
    assert "package-lock" not in ch.text
    assert "+new line" in ch.text and "-old line" in ch.text and "context" not in ch.text
    assert ch.raw_tokens > ch.used_tokens


def test_budget_is_respected_and_drops_are_counted(commit):
    hunks = "".join(f"@@ -{i},1 +{i},1 @@\n-old{i}\n+new{i}\n" for i in range(50))
    c = commit(files=[FileChange("routes/a.js", 50, 50, hunks)])
    ch = chunk_module([c], CFG, budget=40)
    assert ch.used_tokens <= 40 and ch.hunks_dropped > 0
    assert tokens(ch.text) <= 60            # headers add a little; still tiny next to the raw diff


def test_source_ranks_before_tests(commit):
    c = commit(files=[FileChange("tests/a.test.js", 99, 0, DIFF), FileChange("src/a.js", 1, 0, DIFF)])
    ch = chunk_module([c], CFG)
    assert ch.text.index("src/a.js") < ch.text.index("tests/a.test.js")
