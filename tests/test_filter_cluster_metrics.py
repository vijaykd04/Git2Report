from git2report.clustering import cluster, module_of
from git2report.config import Config
from git2report.filtering import decide, filter_commits
from git2report.metrics import compute_metrics
from git2report.models import FileChange

CFG = Config()


def test_filter_removes_merge_typo_wip(commit):
    commits = [commit("feat(auth): add login", h="a"),
               commit("Merge branch 'dev'", is_merge=True, files=[], h="b"),
               commit("fix typo", files=[FileChange("README.md", 1, 1)], h="c"),
               commit("wip", files=[FileChange("a.js", 3, 0)], h="d")]
    kept, decisions = filter_commits(commits, CFG)
    assert [c.hash for c in kept] == ["a"]
    assert [d.reason for d in decisions][1] == "merge commit"


def test_filter_keeps_big_wip(commit):
    big = commit("wip", files=[FileChange("a.js", 50, 0)])
    d = decide(big, CFG)
    assert d.kept and "big change" in d.reason


def test_module_from_scope_then_folder_then_type(commit):
    assert module_of(commit("feat(db): index"), CFG) == ("Database", "scope in message")
    assert module_of(commit("update nav", files=[FileChange("components/Nav.jsx", 5, 1)]), CFG) == ("Components", "top folder by lines")
    assert module_of(commit("docs: notes", files=[FileChange("notes.md", 1, 0)]), CFG) == ("Documentation", "commit type")
    assert module_of(commit("misc", files=[FileChange("notes.md", 1, 0)]), CFG) == ("Other", "fallback")


def test_folder_rule_skips_generic_src_and_junk(commit):
    c = commit("add thing", files=[FileChange("package-lock.json", 500, 0), FileChange("src/billing/pay.py", 4, 0)])
    assert module_of(c, CFG)[0] == "Billing"


def test_cluster_orders_biggest_first_and_records_reason(commit):
    commits = [commit("feat(ui): a", h="1"), commit("feat(auth): b", h="2"), commit("fix(auth): c", h="3")]
    groups = cluster(commits, CFG)
    assert list(groups) == ["Authentication", "UI"]
    assert commits[0].module_reason == "scope in message"


def test_metrics_ignore_junk_and_split_tests(commit):
    commits = [commit("feat(auth): a", files=[FileChange("routes/auth.js", 20, 0), FileChange("tests/auth.test.js", 5, 0),
                                              FileChange("package-lock.json", 400, 0)], author="A"),
               commit("fix(auth): b", files=[FileChange("routes/auth.js", 5, 0)], author="B")]
    groups = cluster(commits, CFG)
    m = compute_metrics(commits, groups, CFG, total_commits_seen=4)
    assert m["commits"] == 2 and m["commits_seen_before_filter"] == 4
    assert m["lines_changed"] == 30 and m["lines_changed_incl_junk"] == 430
    assert m["test_to_code_ratio"] == 0.2
    assert m["authors"] == 2 and m["top_module"] == "Authentication"
    assert m["commits_by_type"] == {"feat": 1, "fix": 1}


def test_module_ignores_test_files_when_source_also_changed(commit):
    c = commit("Fix parsing bug", files=[FileChange("tests/test_parser.py", 200, 0), FileChange("src/parser/core.py", 3, 1)])
    assert module_of(c, CFG)[0] == "Parser"            # not 'Tests', even though tests changed more lines


def test_module_falls_back_to_tests_when_only_tests_changed(commit):
    c = commit("Add more tests", files=[FileChange("tests/test_parser.py", 20, 0)])
    assert module_of(c, CFG)[0] == "Tests"
