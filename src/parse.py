"""Parse the source repo's README markdown job table into Job records.

Each job row looks like:
    | **Company** | Role title | Location | 9m | ✅ Sponsor | [<img ...>](https://apply-url) |

Notes handled here:
- Company is wrapped in **bold**.
- Titles are truncated in the source with a trailing "..." or "…".
- The Visa cell may be empty.
- The Apply cell is a markdown link wrapping an <img>; we extract the URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Matches the (last) markdown link target in a cell: [ ... ](URL)
_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)")
# A table row we care about starts with "| **" (bolded company). This skips the
# header row ("| Company | Role | ...") and the "|---|" separator.
_JOB_ROW_RE = re.compile(r"^\|\s*\*\*")


@dataclass(frozen=True)
class Job:
    company: str
    title: str
    location: str
    posted: str
    visa: str
    url: str

    @property
    def title_truncated(self) -> bool:
        return self.title.endswith("...") or self.title.endswith("…")


def _clean(cell: str) -> str:
    """Strip markdown bold markers and collapse whitespace in a table cell."""
    return cell.replace("**", "").strip()


def parse_readme(markdown: str) -> list[Job]:
    """Return every job row found in the README markdown."""
    jobs: list[Job] = []
    for line in markdown.splitlines():
        if not _JOB_ROW_RE.match(line):
            continue

        # Split on unescaped pipes. A leading/trailing pipe yields empty first/last
        # fields, so drop those before indexing.
        cells = [c for c in line.split("|")]
        if cells and cells[0].strip() == "":
            cells = cells[1:]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        if len(cells) < 6:
            continue

        company = _clean(cells[0])
        title = _clean(cells[1])
        location = _clean(cells[2])
        posted = _clean(cells[3])
        visa = _clean(cells[4])

        link_match = _LINK_RE.search(cells[5])
        if not link_match:
            continue  # no apply URL -> nothing to dedup or link to
        url = link_match.group(1)

        jobs.append(
            Job(
                company=company,
                title=title,
                location=location,
                posted=posted,
                visa=visa,
                url=url,
            )
        )
    return jobs
