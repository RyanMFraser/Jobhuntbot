"""Download the source repo's raw README markdown."""

from __future__ import annotations

import time

import requests

_HEADERS = {"User-Agent": "Jobhuntbot/1.0 (+https://github.com/)"}


def fetch_readme(url: str, retries: int = 3, timeout: int = 30) -> str:
    """GET the raw README, retrying transient failures with backoff."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as err:  # network / 5xx / timeout
            last_err = err
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch README from {url}: {last_err}")
