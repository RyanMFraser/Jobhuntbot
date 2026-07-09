"""Jobhuntbot entrypoint: fetch -> parse -> match -> notify -> persist.

Env vars:
  DISCORD_WEBHOOK_URL  (required unless DRY_RUN=1)
  DRY_RUN=1            fetch + match, print matches, post nothing, write no state
  CONFIG_PATH          override path to config.yaml (default: config.yaml)
"""

from __future__ import annotations

import os
import sys

import yaml

from src import state
from src.fetch import fetch_readme
from src.match import filter_jobs
from src.notify import notify
from src.parse import parse_readme


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    dry_run = os.environ.get("DRY_RUN") == "1"
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")

    if not webhook and not dry_run:
        print("ERROR: DISCORD_WEBHOOK_URL is not set (or use DRY_RUN=1).", file=sys.stderr)
        return 2

    config = load_config(config_path)

    markdown = fetch_readme(config["source_readme"])
    all_jobs = parse_readme(markdown)
    matched = filter_jobs(all_jobs, config)
    print(f"Parsed {len(all_jobs)} jobs; {len(matched)} match your profile.")

    seen = state.load()
    first_run = state.is_empty(seen)

    # New = matched jobs whose apply URL we haven't recorded yet.
    new_jobs = [j for j in matched if j.url not in seen]
    print(f"{len(new_jobs)} are new (not in state).")

    if dry_run:
        for j in new_jobs:
            flag = " [TRUNC]" if j.title_truncated else ""
            print(f"  • {j.company} — {j.title}{flag} | {j.location} | {j.visa} | {j.url}")
        print("DRY_RUN=1: nothing sent, state not written.")
        return 0

    if first_run:
        # Seed silently to avoid flooding the channel on day one.
        print("First run: seeding state silently (no notifications).")
        state.mark_seen(seen, [j.url for j in matched])
    else:
        cap = int(config.get("per_run_cap", 15))
        to_send = new_jobs[:cap]
        extra = len(new_jobs) - len(to_send)
        if to_send:
            notify(webhook, to_send, extra_count=extra)
            print(f"Notified {len(to_send)} job(s)" + (f" (+{extra} capped)." if extra else "."))
        # Mark ALL new matches seen (including capped extras) so they don't re-fire.
        state.mark_seen(seen, [j.url for j in new_jobs])

    seen = state.prune(seen, int(config.get("prune_after_days", 21)))
    state.save(seen)
    print(f"State now tracks {len(seen)} job(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
