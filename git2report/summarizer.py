"""STEP 6: turn one module's commits + short code into plain sentences.

The AI only ever writes words. It is never asked for numbers or commit IDs, and its answer is
checked before use. If the model is missing, answers badly, or breaks the rules, we fall back to
an offline sentence built from the commit messages themselves, and the report says so."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from git2report.models import CommitRecord
from git2report.rules import commit_type, parse_conventional

STYLE = {
    "guide": "formal, academic tone; focus on milestones and design",
    "client": "simple business language; focus on what users can now do",
    "team": "release-notes style; concise and technical",
}
FILE_NAME = re.compile(r"\b[\w\-/]+\.(?:js|jsx|ts|tsx|py|java|css|html|json|md|go|rs|c|cpp|sh|yml|yaml)\b", re.I)


@dataclass
class SummaryRequest:
    module: str
    commits: list[CommitRecord]
    code_text: str
    audience: str = "guide"

    @property
    def prompt(self) -> str:
        msgs = "\n".join(f"- {c.subject}" for c in self.commits)
        return (
            f"Audience: {self.audience} ({STYLE[self.audience]}). The reader is not technical.\n"
            "Task: write 2 simple sentences about these changes.\n"
            "Rules: do not write numbers or file names. Use only the information below.\n"
            f"Module: {self.module}\nCommits:\n{msgs}\nCode changes:\n{self.code_text[:1500]}\n"
            'Return only JSON: {"summary": "..."}'
        )


@dataclass
class Summary:
    text: str
    mode: str                 # "ai" or "offline"
    flagged: bool = False     # True when an AI answer was rejected by our checks
    note: str = ""


TEAM_LABEL = {"feat": "Added", "fix": "Fixed", "perf": "Improved", "refactor": "Refactored", "docs": "Docs",
              "test": "Tests", "style": "Style", "chore": "Chores", "ci": "CI", "build": "Build"}
USER_FACING = {"feat", "fix", "perf", None}


def _clean(desc: str) -> str:
    desc = re.sub(r"\s*\(#\d+\)\s*$", "", desc).rstrip(" .;:")          # drop '(#123)' and trailing dots
    return (desc[0].upper() + desc[1:]) if desc else ""


def _items(req: SummaryRequest) -> list[tuple[str | None, str]]:
    out = []
    for c in req.commits:
        _, _, desc = parse_conventional(c.subject)
        if _clean(desc):
            out.append((commit_type(c.subject), _clean(desc)))
    return out


def _joined(descs: list[str], sep: str, limit: int = 3) -> str:
    extra = f" (and {len(descs) - limit} more)" if len(descs) > limit else ""
    return sep.join(descs[:limit]) + extra


def offline_sentence(req: SummaryRequest) -> str:
    """Wording built from the commit messages only. The audience changes WHAT is shown and HOW it is laid out:
    guide = full list, client = user-facing work only, team = release-notes grouped by type."""
    items = _items(req)
    if not items:
        return "Changes were made in this module."
    if req.audience == "client":
        shown = [d for t, d in items if t in USER_FACING]
        if not shown:
            return "No user-facing changes; internal work only."
        return f"What is new or improved: {_joined(shown, '; ')}."
    if req.audience == "team":
        groups: dict[str, list[str]] = {}
        for t, d in items:
            label = TEAM_LABEL.get(t, "Changed")
            if label in ("Added", "Fixed"):                       # 'Added: Add login' reads badly; drop the repeated verb
                stripped = re.sub(r"^(add|adds|added|fix|fixes|fixed)\s+", "", d, flags=re.I)
                d = (stripped[0].upper() + stripped[1:]) if stripped else d
            groups.setdefault(label, []).append(d)
        return " ".join(f"{label}: {_joined(ds, ', ', 2)}." for label, ds in groups.items())
    return f"Work completed: {_joined([d for _, d in items], '; ')}."


def find_issues(text: str) -> list[str]:
    issues = []
    if not text.strip():
        issues.append("empty answer")
    if re.search(r"\d", text):
        issues.append("contains a number")
    if FILE_NAME.search(text):
        issues.append("mentions a file name")
    return issues


def parse_model_json(raw: str) -> str | None:
    """Pull the 'summary' string out of the model's answer; tolerate extra text around the JSON."""
    for candidate in (raw, *re.findall(r"\{.*\}", raw, flags=re.S)):
        try:
            data = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("summary"), str):
            return data["summary"].strip()
    return None


class OfflineSummarizer:
    mode = "offline"
    label = "offline mode (no AI; wording taken from the commit messages)"

    def summarize(self, req: SummaryRequest) -> Summary:
        return Summary(offline_sentence(req), "offline")


class OllamaSummarizer:
    mode = "ai"

    def __init__(self, model: str = "llama3:8b", host: str | None = None,
                 chat: Callable[[str], str] | None = None, retries: int = 1):
        import os
        self.model = model or "llama3:8b"
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.retries = retries
        self._custom_chat = chat is not None
        self._chat = chat or (lambda p: self._ollama_call(p, True))
        self._ask = chat or (lambda p: self._ollama_call(p, False))
        self.label = f"local AI model Ollama ({self.model}) (answers checked by code)"

    def _ollama_call(self, prompt: str, json_mode: bool) -> str:
        # 1. Try python package if installed
        try:
            import ollama
            client = ollama.Client(host=self.host)
            kwargs = {"format": "json"} if json_mode else {}
            resp = client.chat(model=self.model, options={"temperature": 0.1},
                               messages=[{"role": "user", "content": prompt}], **kwargs)
            return resp["message"]["content"]
        except Exception:
            pass

        # 2. Zero-dependency fallback to local Ollama HTTP REST API
        import json
        import urllib.request
        import urllib.error

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1}
        }
        if json_mode:
            payload["format"] = "json"

        endpoint = f"{self.host.rstrip('/')}/api/chat"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data["message"]["content"]
        except urllib.error.URLError as e:
            raise RuntimeError(f"Could not connect to Ollama at {self.host}: {e}") from None

    def ask(self, prompt: str) -> str:
        """Plain-text question to the model (used for the evaluation baseline)."""
        return self._ask(prompt)

    def summarize(self, req: SummaryRequest) -> Summary:
        from git2report.cache import compute_cache_key, default_cache
        cache_key = None
        if not self._custom_chat:
            hashes = [c.hash for c in req.commits]
            cache_key = compute_cache_key("module", req.module, hashes, req.audience, self.model)
            cached = default_cache.get(cache_key)
            if cached:
                return Summary(cached["summary"], "ai", note="(cached)")

        fallback = offline_sentence(req)
        last_note = ""
        for _ in range(self.retries + 1):
            try:
                raw = self._chat(req.prompt)
            except Exception as exc:                          # not installed, not running, timeout...
                return Summary(fallback, "offline", True, f"AI unavailable ({type(exc).__name__}); used offline wording")
            text = parse_model_json(raw)
            if text is None:
                last_note = "model did not return valid JSON"
                continue
            issues = find_issues(text)
            if issues:
                last_note = "AI answer rejected: " + ", ".join(issues)
                continue
            if cache_key:
                default_cache.set(cache_key, text, "ai")
            return Summary(text, "ai")
        return Summary(fallback, "offline", True, f"{last_note}; used offline wording")


def _load_env_file() -> None:
    import os
    from pathlib import Path
    for p in [Path(".env"), Path(__file__).resolve().parent.parent / ".env", Path.home() / ".git2report_env"]:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


class GeminiSummarizer:
    mode = "ai"

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None,
                 chat: Callable[[str], str] | None = None, retries: int = 1):
        import os
        _load_env_file()
        self.model = model or "gemini-2.5-flash"
        if api_key is None:
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        else:
            self.api_key = api_key
        self.retries = retries
        self._custom_chat = chat is not None
        self._chat = chat or self._call_gemini
        self.label = f"Google Gemini ({self.model}) simple plain-language AI"

    def _call_gemini(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Pass --api-key <key> or set $env:GEMINI_API_KEY.")

        import json
        import time
        import urllib.request
        import urllib.error

        models_to_try = [self.model]
        if self.model != "gemini-3.5-flash-lite":
            models_to_try.append("gemini-3.5-flash-lite")

        last_err = None
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=15) as res:
                        data = json.loads(res.read().decode("utf-8"))
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                except urllib.error.HTTPError as e:
                    if e.code == 429 and attempt == 0:
                        time.sleep(1.0)
                        continue
                    err_msg = e.read().decode("utf-8", errors="replace")
                    last_err = RuntimeError(f"Gemini API error ({e.code}): {err_msg}")
                    break  # Break inner loop and try next model candidate
                except Exception as e:
                    last_err = e
                    break

        if last_err:
            raise last_err
        raise RuntimeError("Gemini call failed with unknown error.")

    def ask(self, prompt: str) -> str:
        return self._chat(prompt)

    def summarize(self, req: SummaryRequest) -> Summary:
        fallback = offline_sentence(req)
        if not self.api_key and not self._custom_chat:
            return Summary(fallback, "offline", True, "GEMINI_API_KEY missing; used offline wording")

        from git2report.cache import compute_cache_key, default_cache
        cache_key = None
        if not self._custom_chat:
            hashes = [c.hash for c in req.commits]
            cache_key = compute_cache_key("module", req.module, hashes, req.audience, self.model)
            cached = default_cache.get(cache_key)
            if cached:
                return Summary(cached["summary"], "ai", note="(cached)")

        last_note = ""
        for _ in range(self.retries + 1):
            try:
                raw = self._chat(req.prompt)
            except Exception as exc:
                return Summary(fallback, "offline", True, f"Gemini error ({type(exc).__name__}); used offline wording")
            text = parse_model_json(raw)
            if text is None:
                last_note = "model did not return valid JSON"
                continue
            issues = find_issues(text)
            if issues:
                last_note = "AI answer rejected: " + ", ".join(issues)
                continue
            if cache_key:
                default_cache.set(cache_key, text, "ai")
            return Summary(text, "ai")
        return Summary(fallback, "offline", True, f"{last_note}; used offline wording")


def list_local_ollama_models(host: str | None = None) -> list[str]:
    """Check if Ollama server is running and return list of pulled model names."""
    import json
    import os
    import urllib.request
    target_host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        url = f"{target_host.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=1.5) as r:
            data = json.loads(r.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def get_summarizer(kind: str, model: str = "", api_key: str | None = None, host: str | None = None):
    if kind == "gemini":
        gemini_model = model if model and ":" not in model else "gemini-2.5-flash"
        return GeminiSummarizer(model=gemini_model, api_key=api_key)
    if kind == "ollama":
        ollama_model = model or "llama3:8b"
        return OllamaSummarizer(model=ollama_model, host=host)
    return OfflineSummarizer()

