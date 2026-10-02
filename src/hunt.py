"""Jobhuntbot entrypoint: fetch -> parse -> match -> notify -> persist.

Env vars:
  DISCORD_WEBHOOK_URL  (required unless DRY_RUN=1)
  DRY_RUN=1            fetch + match, print matches, post nothing, write no state
  CONFIG_PATH          override path to config.yaml (default: config.yaml)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import yaml

from src import state
from src.fetch import fetch_text
from src.match import filter_jobs
from src.notify import notify
from src.parse import PARSERS, Job


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect(config: dict) -> list[Job]:
    """Fetch every configured source and return its matching jobs.

    A failing source is logged and skipped so one broken list doesn't stop the run.
    """
    matched: list[Job] = []
    for src in config.get("sources", []):
        name = src.get("name", src["format"])
        try:
            jobs = PARSERS[src["format"]](fetch_text(src["url"]), source=name)
        except Exception as err:  # noqa: BLE001 - keep other sources running
            print(f"WARNING: source {name} failed: {err}", file=sys.stderr)
            continue
        hits = filter_jobs(jobs, config, bool(src.get("require_new_grad_keyword", False)))
        print(f"[{name}] parsed {len(jobs)} jobs; {len(hits)} match.")
        matched.extend(hits)
    return matched


def dedupe(jobs: list[Job]) -> list[Job]:
    """Drop repeats of the same posting listed by several sources (first source wins)."""
    out: list[Job] = []
    keys: set[str] = set()
    for j in jobs:
        jk = state.job_keys(j)
        if keys.isdisjoint(jk):
            out.append(j)
        keys.update(jk)
    return out


def main() -> int:
    dry_run = os.environ.get("DRY_RUN") == "1"
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "")

    if not webhook and not dry_run:
        print("ERROR: DISCORD_WEBHOOK_URL is not set (or use DRY_RUN=1).", file=sys.stderr)
        return 2

    config = load_config(config_path)

    matched = dedupe(collect(config))
    print(f"{len(matched)} unique jobs match your profile.")

    seen = state.load()
    # New = matched jobs we haven't recorded under their URL or company+title.
    new_jobs = [j for j in matched if not state.is_seen(seen, j)]

    # Only ping fresh postings; older new-to-us ones (e.g. from a newly added source)
    # are recorded silently. Jobs with an unknown post date still ping.
    cutoff = datetime.now(timezone.utc) - timedelta(days=float(config.get("max_age_days", 3)))
    fresh = [j for j in new_jobs if j.posted_at is None or j.posted_at >= cutoff]
    fresh.sort(key=lambda j: j.posted_at or datetime.now(timezone.utc), reverse=True)
    print(f"{len(new_jobs)} are new (not in state); {len(fresh)} posted recently enough to ping.")

    cap = int(config.get("per_run_cap", 15))
    to_send = fresh[:cap]
    extra = len(fresh) - len(to_send)

    if dry_run:
        for j in fresh:
            flag = " [TRUNC]" if j.title_truncated else ""
            print(f"  • [{j.source}] {j.company} — {j.title}{flag} | {j.location} | "
                  f"{j.visa or '?'} | {j.posted} | {j.url}")
        print("DRY_RUN=1: nothing sent, state not written.")
        return 0

    if to_send:
        notify(webhook, to_send, extra_count=extra)
        print(f"Notified {len(to_send)} job(s)" + (f" (+{extra} capped)." if extra else "."))
    # Mark ALL new matches seen (including stale and capped ones) so they don't re-fire.
    state.mark_seen(seen, new_jobs)

    seen = state.prune(seen, int(config.get("prune_after_days", 60)))
    state.save(seen)
    print(f"State now tracks {len(seen)} key(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
