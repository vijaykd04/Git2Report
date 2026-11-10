from git2report.summarizer import (GeminiSummarizer, OfflineSummarizer, OllamaSummarizer, SummaryRequest, find_issues,
                                   offline_sentence, parse_model_json)


def req(commit):
    return SummaryRequest("Authentication", [commit("feat(auth): add JWT login"), commit("fix(auth): handle null user")], "+code", "guide")


def test_gemini_summarizer_uses_plain_answer(commit):
    s = GeminiSummarizer(api_key="fake-key", chat=lambda p: '{"summary": "Users can now sign in easily with protected accounts."}').summarize(req(commit))
    assert s.mode == "ai" and s.text == "Users can now sign in easily with protected accounts."


def test_gemini_missing_key_falls_back(commit):
    s = GeminiSummarizer(api_key="").summarize(req(commit))
    assert s.mode == "offline" and "GEMINI_API_KEY missing" in s.note


def test_prompt_contains_rules_and_no_hashes(commit):
    p = req(commit).prompt
    assert "do not write numbers or file names" in p and "Return only JSON" in p
    assert "abc1234" not in p                       # commit IDs are never given to the AI


def test_offline_sentence(commit):
    assert offline_sentence(req(commit)) == "Work completed: Add JWT login; Handle null user."


def test_parse_model_json_tolerates_noise():
    assert parse_model_json('{"summary": "Login was secured."}') == "Login was secured."
    assert parse_model_json('Sure! {"summary": "Fixed."} Hope that helps') == "Fixed."
    assert parse_model_json("not json") is None
    assert parse_model_json('{"other": 1}') is None


def test_find_issues():
    assert find_issues("Login was made safer.") == []
    assert "contains a number" in find_issues("Speed improved by 35%.")
    assert "mentions a file name" in find_issues("Edited auth.js to fix it.")
    assert "empty answer" in find_issues("  ")


def test_good_ai_answer_is_used(commit):
    s = OllamaSummarizer(chat=lambda p: '{"summary": "Login was secured."}').summarize(req(commit))
    assert (s.text, s.mode, s.flagged) == ("Login was secured.", "ai", False)


def test_bad_ai_answer_is_retried_then_falls_back(commit):
    calls = []
    def chat(p):
        calls.append(1)
        return '{"summary": "Speed improved by 35%."}'
    s = OllamaSummarizer(chat=chat, retries=1).summarize(req(commit))
    assert len(calls) == 2 and s.mode == "offline" and s.flagged and "contains a number" in s.note


def test_second_try_can_succeed(commit):
    answers = iter(['garbage', '{"summary": "Login was secured."}'])
    s = OllamaSummarizer(chat=lambda p: next(answers)).summarize(req(commit))
    assert s.mode == "ai" and s.text == "Login was secured."


def test_unavailable_ai_falls_back_without_crashing(commit):
    def chat(p):
        raise ConnectionError("ollama is not running")
    s = OllamaSummarizer(chat=chat).summarize(req(commit))
    assert s.mode == "offline" and s.flagged and "ConnectionError" in s.note


def test_offline_summarizer(commit):
    assert OfflineSummarizer().summarize(req(commit)).mode == "offline"


def test_offline_sentence_cleans_pr_numbers_and_double_dots(commit):
    r = SummaryRequest("X", [commit("Start 8.6.0."), commit("Add `Parameter.spec` (#3877)")], "", "guide")
    assert offline_sentence(r) == "Work completed: Start 8.6.0; Add `Parameter.spec`."


def _aud(commit, audience):
    cs = [commit("feat(ui): add dark mode"), commit("fix(ui): button overlap"), commit("refactor(ui): split styles"),
          commit("test(ui): add snapshot tests")]
    return offline_sentence(SummaryRequest("UI", cs, "", audience))


def test_audience_changes_the_offline_wording(commit):
    guide, client, team = _aud(commit, "guide"), _aud(commit, "client"), _aud(commit, "team")
    assert len({guide, client, team}) == 3
    assert client == "What is new or improved: Add dark mode; Button overlap."      # refactor/test hidden from clients
    assert team == "Added: Dark mode. Fixed: Button overlap. Refactored: Split styles. Tests: Add snapshot tests."
    assert guide.startswith("Work completed: Add dark mode; Button overlap; Split styles (and 1 more)")


def test_client_audience_with_only_internal_work(commit):
    r = SummaryRequest("X", [commit("chore: bump deps"), commit("test: more tests")], "", "client")
    assert offline_sentence(r) == "No user-facing changes; internal work only."


def test_team_wording_works_without_conventional_prefixes(commit):
    r = SummaryRequest("X", [commit("Add login page"), commit("Fixed crash on start")], "", "team")
    assert offline_sentence(r) == "Added: Login page. Fixed: Crash on start."
