import os

import yaml

from src.match import filter_jobs
from src.parse import parse_readme

FIXTURE = os.path.join(os.path.dirname(__file__), "sample_readme.md")
CONFIG = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load():
    with open(FIXTURE, encoding="utf-8") as f:
        jobs = parse_readme(f.read())
    with open(CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return jobs, config


def matched_titles():
    jobs, config = load()
    return {j.company for j in filter_jobs(jobs, config)}


def test_data_ml_california_sponsor_passes():
    companies = matched_titles()
    # TikTok ML Engineer, San Jose CA, H-1B -> pass
    assert "TikTok" in companies
    # Northrop Data Scientist, California, no visa -> rejected (visa_required)
    # SS&C Data Platform, Kansas City -> rejected (location not CA)


def test_non_data_role_rejected():
    # Trace3 DevOps is sponsor + US but not a data/ml role.
    assert "Trace3" not in matched_titles()


def test_senior_role_excluded():
    # BigCo "Senior Data Scientist" is CA + sponsor but excluded by "senior".
    assert "BigCo" not in matched_titles()


def test_non_us_rejected_even_if_sponsor():
    # GlobalCorp Data Engineer, Bangalore India, sponsor -> rejected by location.
    assert "GlobalCorp" not in matched_titles()


def test_no_visa_rejected():
    # Northrop is a CA data scientist but has an empty visa cell.
    assert "Northrop Grumman" not in matched_titles()


def test_out_of_state_data_role_rejected():
    # SS&C Data Platform is sponsor + data but Kansas City, MO.
    assert "SS&C Technologies" not in matched_titles()
