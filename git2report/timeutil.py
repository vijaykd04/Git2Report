from __future__ import annotations

import re
from datetime import datetime, timedelta

from git2report.models import GitReportError


def parse_since(text: str, now: datetime | None = None) -> datetime:
    """'7d', '2w', '12h' (relative to now) or an ISO date such as '2026-10-01'."""
    now = now or datetime.now()
    m = re.fullmatch(r"\s*(\d+)\s*([hdw])\s*", text.lower())
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return now - timedelta(**{{"h": "hours", "d": "days", "w": "weeks"}[unit]: n})
    try:
        return datetime.fromisoformat(text.strip())
    except ValueError:
        raise GitReportError(f"Cannot understand --since '{text}'. Use e.g. 7d, 2w, 12h or 2026-10-01.") from None
