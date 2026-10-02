import os

import yaml

from src.match import filter_jobs
from src.parse import parse_readme, parse_simplify_json, parse_speedyapply

HERE = os.path.dirname(__file__)
CONFIG = os.path.join(HERE, "..", "config.yaml")


def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def _config():
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def zapply_companies():
    # zapply mixes in experienced roles, so it's run with require_new_grad_keyword.
    jobs = parse_readme(_read("sample_readme.md"))
    return {j.company for j in filter_jobs(jobs, _config(), require_new_grad_keyword=True)}


def curated_companies(parser, fixture):
    jobs = parser(_read(fixture))
    return {j.company for j in filter_jobs(jobs, _config(), require_new_grad_keyword=False)}


def test_new_grad_swe_in_california_passes():
    assert "Adobe" in zapply_companies()


def test_associate_data_scientist_in_california_passes():
    # "Associate" is a new-grad keyword; empty visa cell is "unknown", not blocked.
    assert "Northrop Grumman" in zapply_companies()


def test_title_without_new_grad_signal_rejected_for_noisy_source():
    # TikTok "Machine Learning Engineer..." is CA + ML but says nothing about new grad.
    assert "TikTok" not in zapply_companies()


def test_level_ii_and_interns_rejected():
    companies = zapply_companies()
    assert "Rivian" not in companies
    assert "Snap" not in companies


def test_non_swe_role_rejected():
    assert "Trace3" not in zapply_companies()


def test_senior_role_excluded():
    assert "BigCo" not in zapply_companies()


def test_non_california_rejected():
    companies = zapply_companies()
    assert "GlobalCorp" not in companies
    assert "SS&C Technologies" not in companies


def test_speedyapply_curated_list():
    companies = curated_companies(parse_speedyapply, "sample_speedyapply.md")
    assert companies == {"Adobe", "SpaceX"}  # Amazon is "II" and in WA


def test_simplify_curated_list():
    companies = curated_companies(parse_simplify_json, "sample_listings.json")
    # Pinterest: SF new grad SWE. Acme: citizenship required (blocked by visa: not_blocked).
    # OldCo: inactive. Quora: Texas.
    assert companies == {"Pinterest"}


def test_word_boundaries():
    from src.parse import Job

    def job(title, location="San Francisco, CA"):
        return Job("X", title, location, "", "", "https://x")

    cfg = _config()
    # "staff" inside "Member of Technical Staff" is not a seniority signal.
    assert filter_jobs([job("Member of Technical Staff - New Grad")], cfg)
    assert not filter_jobs([job("Staff Software Engineer")], cfg)
    # "ca" must be a whole word: "Chicago" / "Jamaica" don't count as California.
    assert not filter_jobs([job("Software Engineer New Grad", "Kingston, Jamaica")], cfg)
    # "2027" isn't excluded by the "2" (level II) rule.
    assert filter_jobs([job("Software Engineer, 2027 New Grad")], cfg)
