"""Tests for deterministic risk scoring."""

import pytest

from phish_assistant.models import ClassifierResult, Indicator
from phish_assistant.scoring import assess_risk, indicator_points, level_for, risk_score


def result(p: float) -> ClassifierResult:
    """Build a classifier result with the given phishing probability."""
    return ClassifierResult(label_scores={}, phishing_probability=p, truncated=False)


def ind(category: str) -> Indicator:
    """Build an indicator; text and offsets don't matter for scoring."""
    return Indicator(category, "x", 0, 1)


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0.0, "Low"),
        (0.3499, "Low"),
        (0.35, "Medium"),
        (0.6499, "Medium"),
        (0.65, "High"),
        (1.0, "High"),
    ],
)
def test_level_boundaries(score: float, level: str) -> None:
    assert level_for(score) == level


@pytest.mark.parametrize(
    ("p", "points", "expected"),
    [
        (0.0, 0, 0.0),
        (1.0, 0, 0.6),
        (0.0, 5, 0.4),
        (0.0, 50, 0.4),  # points are capped at 5
        (0.45, 1, 0.35),  # exactly the Medium threshold
        (0.55, 4, 0.65),  # exactly the High threshold
    ],
)
def test_risk_score(p: float, points: int, expected: float) -> None:
    assert risk_score(p, points) == expected


def test_every_match_counts_including_repeats() -> None:
    twice = [ind("suspicious_language"), ind("suspicious_language")]
    assert indicator_points(twice, []) == 2


def test_url_findings_add_one_point_each() -> None:
    assert indicator_points([ind("urgency")], ["a", "b"]) == 4


@pytest.mark.parametrize(
    ("p", "indicators", "urls", "level"),
    [
        (0.0, [], [], "Low"),
        (1.0, [], [], "Medium"),  # classifier alone can't reach High
        (
            0.0,
            [ind("payment_request"), ind("urgency")],
            [],
            "Medium",
        ),  # rules alone can't either
        (0.9, [ind("credential_request"), ind("threat")], ["No HTTPS"], "High"),
        (0.875, [], [], "Medium"),  # the misread password-reset sample
    ],
)
def test_assess_risk_levels(p: float, indicators: list, urls: list, level: str) -> None:
    assert assess_risk(result(p), indicators, urls).level == level


def test_credential_plus_url_raised_to_medium() -> None:
    assessment = assess_risk(result(0.0), [ind("credential_request")], ["Raw IP"])
    assert assessment.score < 0.35
    assert assessment.level == "Medium"
    assert any("Raised to Medium" in r for r in assessment.reasons)


def test_credential_without_url_not_raised() -> None:
    assert assess_risk(result(0.0), [ind("credential_request")], []).level == "Low"


def test_reasons_always_present_and_readable() -> None:
    assessment = assess_risk(
        result(0.91),
        [ind("urgency"), ind("urgency"), ind("payment_request")],
        ["Link uses a URL shortener."],
    )
    assert assessment.reasons == [
        "Classifier phishing probability 0.91",
        "2 urgency phrases",
        "1 payment request phrase",
        "Link uses a URL shortener.",
    ]
    assert assess_risk(result(0.0), [], []).reasons == [
        "Classifier phishing probability 0.00",
        "No social-engineering phrases found",
    ]


def test_deterministic() -> None:
    args = (result(0.7), [ind("threat")], ["x"])
    assert assess_risk(*args) == assess_risk(*args)
