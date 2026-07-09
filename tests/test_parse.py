import os

from src.parse import parse_readme

FIXTURE = os.path.join(os.path.dirname(__file__), "sample_readme.md")


def load_jobs():
    with open(FIXTURE, encoding="utf-8") as f:
        return parse_readme(f.read())


def test_parses_all_job_rows_and_skips_header():
    jobs = load_jobs()
    # 6 data rows in the fixture; header/separator/prose ignored.
    assert len(jobs) == 6


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
