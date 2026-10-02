"""Parse each supported source into Job records.

Supported source formats:
- "zapply"       zapplyjobs/New-Grad-Jobs-2027 README table:
                   | **Company** | Role | Location | 9m | ✅ Sponsor | [<img ...>](https://apply-url) |
- "speedyapply"  speedyapply/<year>-SWE-College-Jobs NEW_GRAD_USA.md HTML-ish table:
                   | <a href=...><strong>Co</strong></a> | Role | Location | [Salary |] <a href="apply">..</a> | 1d |
- "simplify"     SimplifyJobs-style .github/scripts/listings.json (also used by vanshb03).

Notes:
- Zapply truncates long titles with a trailing "..." or "…".
- Visa info is optional; it's normalized to a short human-readable string ("" = unknown).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Matches the (last) markdown link target in a cell: [ ... ](URL)
_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)")
# Matches an HTML anchor target: <a href="URL">
_HREF_RE = re.compile(r'href="(https?://[^"]+)"')
_TAG_RE = re.compile(r"<[^>]+>")
# A zapply row starts with "| **" (bolded company); skips header and "|---|".
_ZAPPLY_ROW_RE = re.compile(r"^\|\s*\*\*")
# A speedyapply row starts with "| <a" (linked company).
_SPEEDY_ROW_RE = re.compile(r"^\|\s*<a\s")
# Relative ages like "13m", "2h", "3d", "2w", "1mo".
_AGE_RE = re.compile(r"^(\d+)\s*(mo|m|h|d|w)$")
_AGE_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}

# Simplify's `sponsorship` field -> display string.
_SIMPLIFY_SPONSORSHIP = {
    "Offers Sponsorship": "✅ Sponsor",
    "Does Not Offer Sponsorship": "❌ No sponsorship",
    "U.S. Citizenship is Required": "🇺🇸 US citizenship required",
}


@dataclass(frozen=True)
class Job:
    company: str
    title: str
    location: str
    posted: str
    visa: str
    url: str
    source: str = ""
    posted_at: datetime | None = None

    @property
    def title_truncated(self) -> bool:
        return self.title.endswith("...") or self.title.endswith("…")


def _clean(cell: str) -> str:
    """Strip markdown bold markers and collapse whitespace in a table cell."""
    return cell.replace("**", "").strip()


def _strip_html(cell: str) -> str:
    return html.unescape(_TAG_RE.sub("", cell)).strip()


def _table_cells(line: str) -> list[str]:
    """Split a markdown table row, dropping the empty edge fields."""
    cells = line.split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return cells


def parse_age(age: str, now: datetime | None = None) -> datetime | None:
    """Turn a relative age like "13m" / "3d" into an absolute UTC time (None if unknown)."""
    m = _AGE_RE.match(age.strip().casefold())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    now = now or datetime.now(timezone.utc)
    if unit == "mo":
        return now - timedelta(days=30 * n)
    return now - timedelta(**{_AGE_UNITS[unit]: n})


def parse_readme(markdown: str, source: str = "zapply") -> list[Job]:
    """Return every job row found in a zapply-style README."""
    jobs: list[Job] = []
    for line in markdown.splitlines():
        if not _ZAPPLY_ROW_RE.match(line):
            continue
        cells = _table_cells(line)
        if len(cells) < 6:
            continue

        link_match = _LINK_RE.search(cells[5])
        if not link_match:
            continue  # no apply URL -> nothing to dedup or link to

        posted = _clean(cells[3])
        jobs.append(
            Job(
                company=_clean(cells[0]),
                title=_clean(cells[1]),
                location=_clean(cells[2]),
                posted=posted,
                visa=_clean(cells[4]),
                url=link_match.group(1),
                source=source,
                posted_at=parse_age(posted),
            )
        )
    return jobs


def parse_speedyapply(markdown: str, source: str = "speedyapply") -> list[Job]:
    """Return every job row in a speedyapply NEW_GRAD_*.md file.

    The FAANG/Quant tables have a Salary column and the "Other" table doesn't, so
    the apply link and age are read from the end of the row.
    """
    jobs: list[Job] = []
    for line in markdown.splitlines():
        if not _SPEEDY_ROW_RE.match(line):
            continue
        cells = _table_cells(line)
        if len(cells) < 5:
            continue

        href = _HREF_RE.search(cells[-2])
        if not href:
            continue

        age = _strip_html(cells[-1])
        jobs.append(
            Job(
                company=_strip_html(cells[0]),
                title=_strip_html(cells[1]),
                location=_strip_html(cells[2]),
                posted=age,
                visa="",
                url=html.unescape(href.group(1)),
                source=source,
                posted_at=parse_age(age),
            )
        )
    return jobs


def parse_simplify_json(text: str, source: str = "simplify") -> list[Job]:
    """Return active, visible listings from a SimplifyJobs-style listings.json."""
    jobs: list[Job] = []
    for item in json.loads(text):
        if not item.get("active") or not item.get("is_visible", True):
            continue
        url = item.get("url") or ""
        if not url.startswith("http"):
            continue

        posted_at = None
        ts = item.get("date_posted")
        if isinstance(ts, (int, float)) and ts > 0:
            posted_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        jobs.append(
            Job(
                company=(item.get("company_name") or "").strip(),
                title=(item.get("title") or "").strip(),
                location="; ".join(item.get("locations") or []),
                posted=posted_at.strftime("%b %d") if posted_at else "",
                visa=_SIMPLIFY_SPONSORSHIP.get(item.get("sponsorship") or "", ""),
                url=url,
                source=source,
                posted_at=posted_at,
            )
        )
    return jobs


PARSERS = {
    "zapply": parse_readme,
    "speedyapply": parse_speedyapply,
    "simplify": parse_simplify_json,
}
