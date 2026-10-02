import os

from src.parse import parse_readme

FIXTURE = os.path.join(os.path.dirname(__file__), "sample_readme.md")


def load_jobs():
    with open(FIXTURE, encoding="utf-8") as f:
        return parse_readme(f.read())


def test_parses_all_job_rows_and_skips_header():
    jobs = load_jobs()
    # 9 data rows in the fixture; header/separator/prose ignored.
    assert len(jobs) == 9


def test_strips_bold_and_extracts_fields():
    tiktok = load_jobs()[0]
    assert tiktok.company == "TikTok"
    assert tiktok.location == "San Jose, California"
    assert tiktok.visa == "🏛 H-1B Co."
    assert tiktok.url == "https://lifeattiktok.com/position/7509598272319719687"


def test_detects_truncated_title():
    tiktok = load_jobs()[0]
    assert tiktok.title_truncated is True


def test_empty_visa_cell_is_empty_string():
    northrop = load_jobs()[1]
    assert northrop.visa == ""
    assert northrop.title_truncated is False


def test_apply_url_is_the_link_target_not_the_image():
    for job in load_jobs():
        assert job.url.startswith("http")
        assert "images/apply.png" not in job.url


def test_parse_age():
    from datetime import datetime, timedelta, timezone

    from src.parse import parse_age

    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert parse_age("13m", now) == now - timedelta(minutes=13)
    assert parse_age("3d", now) == now - timedelta(days=3)
    assert parse_age("Date unknown", now) is None


def test_speedyapply_handles_tables_with_and_without_salary():
    from src.parse import parse_speedyapply

    path = os.path.join(os.path.dirname(__file__), "sample_speedyapply.md")
    with open(path, encoding="utf-8") as f:
        jobs = parse_speedyapply(f.read())
    assert [j.company for j in jobs] == ["Adobe", "Amazon", "SpaceX"]
    spacex = jobs[2]
    assert spacex.title == "New Graduate Engineer - Software - Starfall"
    assert spacex.location == "Hawthorne, CA"
    assert spacex.url == "https://boards.greenhouse.io/spacex/jobs/8854394002?gh_jid=8854394002&x=1"
    assert spacex.posted == "2d"


def test_simplify_json_skips_inactive_and_maps_sponsorship():
    from src.parse import parse_simplify_json

    path = os.path.join(os.path.dirname(__file__), "sample_listings.json")
    with open(path, encoding="utf-8") as f:
        jobs = parse_simplify_json(f.read())
    assert [j.company for j in jobs] == ["Pinterest", "Acme Defense", "Quora"]
    assert jobs[0].location == "SF; Remote in USA"
    assert jobs[0].visa == ""
    assert "citizenship" in jobs[1].visa.casefold()
    assert jobs[0].posted_at is not None
