import pytest

from app.core.models import Evidence
from app.core.scorer import score_run, signal, weighted_mean

SOURCE = Evidence(url="https://example.com/evidence", title="Evidence", source="Test")


def example(name, score):
    return signal(name, "Test", score=score, evidence=[SOURCE] if score is not None else [])


@pytest.mark.parametrize(
    "hype,support,verdict",
    [
        (60, 40, "High"),
        (59.99, 40, "Low"),
        (40, 20, "Elevated"),
        (40, 20.01, "Low"),
        (100, 49.99, "Elevated"),
        (100, 50, "Elevated"),
        (10, 90, "Low"),
        (80, None, "Insufficient data"),
    ],
)
def test_verdict_boundaries(hype, support, verdict):
    signals = [example(name, hype) for name in ["video_velocity", "search_spike", "tip_density"]]
    signals += [example("news_coverage", support)]
    assert score_run(signals)[2] == verdict


def test_missing_signals_are_not_zero():
    signals = [example("video_velocity", 100), example("search_spike", None), example("tip_density", 0)]
    assert weighted_mean(signals, "hype") == 60
    assert score_run(signals)[2] == "Insufficient data"


def test_scored_signal_requires_evidence():
    assert not signal("search_spike", "Test", score=80).has_data
    assert example("search_spike", 200).score == 100
    assert example("search_spike", -10).score == 0


def test_single_max_signal_elevates_with_weak_support():
    signals = [
        example("video_velocity", 100),
        example("search_spike", 0),
        example("tip_density", 0),
        example("news_coverage", 49),
    ]
    assert score_run(signals)[2] == "Elevated"
    assert all(r.evidence for r in score_run(signals)[3])
