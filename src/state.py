"""Load, update, and prune the committed dedup store (state/seen.json).

Format: { "<key>": "<iso8601 first_seen>" }

Each job is stored under two keys: its apply URL, and "ct:<company>|<title>" so the
same posting listed by several sources (with different URLs) only pings once.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone

DEFAULT_PATH = os.path.join("state", "seen.json")

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def load(path: str = DEFAULT_PATH) -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def is_empty(seen: dict[str, str]) -> bool:
    return len(seen) == 0


def _norm(s: str) -> str:
    return _NON_ALNUM.sub(" ", s.casefold()).strip()


def job_keys(job) -> list[str]:
    """Dedup keys for a Job: apply URL plus normalized company+title."""
    return [job.url, f"ct:{_norm(job.company)}|{_norm(job.title)}"]


def is_seen(seen: dict[str, str], job) -> bool:
    return any(k in seen for k in job_keys(job))


def mark_seen(seen: dict[str, str], jobs: list) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        for key in job_keys(job):
            seen.setdefault(key, now)


def prune(seen: dict[str, str], older_than_days: int) -> dict[str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    kept: dict[str, str] = {}
    for url, ts in seen.items():
        try:
            when = datetime.fromisoformat(ts)
        except ValueError:
            kept[url] = ts  # keep unparseable rather than lose dedup
            continue
        if when >= cutoff:
            kept[url] = ts
    return kept


def save(seen: dict[str, str], path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2, sort_keys=True)
        f.write("\n")
