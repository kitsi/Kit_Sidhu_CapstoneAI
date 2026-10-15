"""Deterministic risk-level logic. The LLM never sets the risk level; this does."""

from collections import Counter

from phish_assistant.config import (
    CATEGORY_WEIGHTS,
    CLASSIFIER_WEIGHT,
    HIGH_THRESHOLD,
    INDICATOR_POINTS_CAP,
    INDICATOR_WEIGHT,
    MEDIUM_THRESHOLD,
    URL_FINDING_POINTS,
)
from phish_assistant.models import ClassifierResult, Indicator, RiskAssessment

LEVELS = ("Low", "Medium", "High")


def indicator_points(indicators: list[Indicator], url_findings: list[str]) -> int:
    """Sum category weights for every match, plus points for each URL finding."""
    rule_points = sum(CATEGORY_WEIGHTS[i.category] for i in indicators)
    return rule_points + URL_FINDING_POINTS * len(url_findings)


def risk_score(phishing_probability: float, points: int) -> float:
    """Combine classifier probability and capped indicator points into 0–1."""
    indicator_part = min(1.0, points / INDICATOR_POINTS_CAP)
    score = CLASSIFIER_WEIGHT * phishing_probability + INDICATOR_WEIGHT * indicator_part
    return round(score, 4)  # avoid float noise at the thresholds


def level_for(score: float) -> str:
    """Map a score to Low, Medium, or High."""
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def _indicator_reasons(indicators: list[Indicator]) -> list[str]:
    """Describe matches per category in order of first appearance, e.g. "2 urgency phrases"."""
    counts = Counter(i.category for i in indicators)
    reasons = []
    for category, count in counts.items():
        noun = "phrase" if count == 1 else "phrases"
        reasons.append(f"{count} {category.replace('_', ' ')} {noun}")
    return reasons


def _needs_medium_floor(indicators: list[Indicator], url_findings: list[str]) -> bool:
    """A credential request plus a suspicious link is the classic phishing pattern."""
    return bool(url_findings) and any(i.category == "credential_request" for i in indicators)


def assess_risk(
    classifier_result: ClassifierResult,
    indicators: list[Indicator],
    url_findings: list[str],
) -> RiskAssessment:
    """Return the risk level, score, and reasons. Pure and deterministic."""
    points = indicator_points(indicators, url_findings)
    score = risk_score(classifier_result.phishing_probability, points)
    level = level_for(score)
    reasons = [f"Classifier phishing probability {classifier_result.phishing_probability:.2f}"]
    reasons += _indicator_reasons(indicators) or ["No social-engineering phrases found"]
    reasons += url_findings
    if level == "Low" and _needs_medium_floor(indicators, url_findings):
        level = "Medium"
        reasons.append("Raised to Medium: credential request combined with a suspicious link")
    return RiskAssessment(level=level, score=score, reasons=reasons)
