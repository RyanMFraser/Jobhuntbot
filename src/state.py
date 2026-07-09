"""Load, update, and prune the committed dedup store (state/seen.json).

Format: { "<apply_url>": "<iso8601 first_seen>" }
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

DEFAULT_PATH = os.path.join("state", "seen.json")


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


def mark_seen(seen: dict[str, str], urls: list[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for url in urls:
        seen.setdefault(url, now)


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
