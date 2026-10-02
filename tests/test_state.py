from src import state
from src.parse import Job


def test_same_posting_from_two_sources_is_seen_once():
    a = Job("Pinterest", "University Grad Software Engineer", "SF", "", "", "https://a", "simplify")
    b = Job("pinterest", "University Grad - Software Engineer", "SF", "", "", "https://b", "zapply")
    seen = {}
    state.mark_seen(seen, [a])
    assert state.is_seen(seen, b)
