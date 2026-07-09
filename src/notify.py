"""Post matched jobs to Discord via an Incoming Webhook.

Discord allows up to 10 embeds per message, so we batch. Each job becomes one
embed with company, location, and visa status; the title links to the apply URL.
"""

from __future__ import annotations

import time

import requests

from src.parse import Job

_MAX_EMBEDS_PER_MSG = 10
_COLOR = 0x2ECC71  # green


def _embed(job: Job) -> dict:
    fields = [
        {"name": "Company", "value": job.company or "—", "inline": True},
        {"name": "Location", "value": job.location or "—", "inline": True},
    ]
    if job.visa:
        fields.append({"name": "Visa", "value": job.visa, "inline": True})
    title = job.title or "New role"
    if job.title_truncated:
        title += " (title truncated at source)"
    return {
        "title": title[:256],
        "url": job.url,
        "color": _COLOR,
        "fields": fields,
    }


def _post(webhook_url: str, payload: dict) -> None:
    resp = requests.post(webhook_url, json=payload, timeout=30)
    # Respect Discord rate limiting.
    if resp.status_code == 429:
        retry_after = resp.json().get("retry_after", 1)
        time.sleep(float(retry_after) + 0.5)
        resp = requests.post(webhook_url, json=payload, timeout=30)
    resp.raise_for_status()


def notify(webhook_url: str, jobs: list[Job], extra_count: int = 0) -> None:
    """Send embeds for `jobs`, batched. `extra_count` appends a "+N more" note."""
    if not jobs:
        return
    for i in range(0, len(jobs), _MAX_EMBEDS_PER_MSG):
        batch = jobs[i : i + _MAX_EMBEDS_PER_MSG]
        payload = {"embeds": [_embed(j) for j in batch]}
        _post(webhook_url, payload)
        time.sleep(0.6)  # gentle pacing between messages

    if extra_count > 0:
        _post(
            webhook_url,
            {"content": f"…and **+{extra_count} more** matches this run (capped)."},
        )
