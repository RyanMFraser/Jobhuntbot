"""Filter parsed Jobs down to the ones worth notifying about, per config.yaml."""

from __future__ import annotations

from src.parse import Job

# Substrings that indicate a sponsor-friendly employer in the README's Visa cell.
_SPONSOR_MARKERS = ("sponsor", "h-1b", "h1b")


def _lower(s: str) -> str:
    return s.casefold()


def role_matches(job: Job, roles: dict) -> bool:
    title = _lower(job.title)
    includes = [_lower(k) for k in roles.get("include", [])]
    excludes = [_lower(k) for k in roles.get("exclude", [])]
    if excludes and any(k in title for k in excludes):
        return False
    if not includes:
        return True
    return any(k in title for k in includes)


def location_matches(job: Job, location: dict) -> bool:
    loc = _lower(job.location)
    for bad in (_lower(k) for k in location.get("reject_if_contains", [])):
        if bad and bad in loc:
            return False
    includes = [_lower(k) for k in location.get("include", [])]
    if not includes:
        return True
    return any(k in loc for k in includes)


def visa_matches(job: Job, visa_required: bool) -> bool:
    if not visa_required:
        return True
    cell = _lower(job.visa)
    return any(m in cell for m in _SPONSOR_MARKERS)


def matches(job: Job, config: dict) -> bool:
    return (
        role_matches(job, config.get("roles", {}))
        and location_matches(job, config.get("location", {}))
        and visa_matches(job, config.get("visa_required", False))
    )


def filter_jobs(jobs: list[Job], config: dict) -> list[Job]:
    return [j for j in jobs if matches(j, config)]
