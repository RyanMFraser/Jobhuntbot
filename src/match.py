"""Filter parsed Jobs down to the ones worth notifying about, per config.yaml.

Keyword lists are matched case-insensitively on word boundaries, so "ai" matches
"AI Engineer" but not "Maintenance", and "ii" matches "Engineer II" but not "Hawaii".
"""

from __future__ import annotations

import re
from functools import lru_cache

from src.parse import Job

# Visa cell markers. Negatives are checked first ("No sponsorship" contains "sponsor").
_NO_SPONSOR_MARKERS = ("no sponsor", "not offer", "does not sponsor", "citizenship", "citizen")
_SPONSOR_MARKERS = ("sponsor", "h-1b", "h1b")

# Phrases that contain an excluded word but aren't seniority signals.
_EXCLUDE_EXEMPT = ("member of technical staff", "technical staff")


@lru_cache(maxsize=None)
def _pattern(keywords: tuple[str, ...]) -> re.Pattern | None:
    words = [k.casefold().strip() for k in keywords if k and k.strip()]
    if not words:
        return None
    alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![a-z0-9])(?:{alts})(?![a-z0-9])")


def _has_any(text: str, keywords: list[str]) -> bool:
    pat = _pattern(tuple(keywords))
    return bool(pat and pat.search(text.casefold()))


def role_matches(job: Job, roles: dict) -> bool:
    title = job.title.casefold()
    exclude_text = title
    for phrase in _EXCLUDE_EXEMPT:
        exclude_text = exclude_text.replace(phrase, " ")
    if _has_any(exclude_text, roles.get("exclude", [])):
        return False
    includes = roles.get("include", [])
    return not includes or _has_any(title, includes)


def is_new_grad(job: Job, new_grad: dict, require_keyword: bool) -> bool:
    """Reject interns / experienced roles; for noisy sources, demand a new-grad keyword."""
    if _has_any(job.title, new_grad.get("exclude", [])):
        return False
    if not require_keyword:
        return True
    return _has_any(job.title, new_grad.get("keywords", []))


def location_matches(job: Job, location: dict) -> bool:
    loc = job.location.casefold()
    for bad in (k.casefold() for k in location.get("reject_if_contains", [])):
        if bad and bad in loc:
            return False
    includes = location.get("include", [])
    return not includes or _has_any(loc, includes)


def visa_matches(job: Job, mode: str) -> bool:
    """mode: "any" | "not_blocked" (drop explicit no-sponsor/citizens-only) | "sponsor_only"."""
    if mode == "any":
        return True
    cell = job.visa.casefold()
    if any(m in cell for m in _NO_SPONSOR_MARKERS):
        return False
    if mode == "sponsor_only":
        return any(m in cell for m in _SPONSOR_MARKERS)
    return True


def matches(job: Job, config: dict, require_new_grad_keyword: bool = False) -> bool:
    return (
        role_matches(job, config.get("roles", {}))
        and is_new_grad(job, config.get("new_grad", {}), require_new_grad_keyword)
        and location_matches(job, config.get("location", {}))
        and visa_matches(job, config.get("visa", "any"))
    )


def filter_jobs(jobs: list[Job], config: dict, require_new_grad_keyword: bool = False) -> list[Job]:
    return [j for j in jobs if matches(j, config, require_new_grad_keyword)]
