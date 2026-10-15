"""Orchestration: run every analysis step in order and build the report.

Classifier failure is fatal (no risk level without it); explainer failure is
degraded to the template fallback. Logs stage timings, never email content.
"""

import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from phish_assistant import classifier, explainer
from phish_assistant.classifier import email_text
from phish_assistant.models import (
    AnalysisReport,
    ClassifierResult,
    EmailInput,
    Indicator,
    RiskAssessment,
)
from phish_assistant.rules import find_indicators
from phish_assistant.scoring import assess_risk
from phish_assistant.url_checks import url_findings

log = logging.getLogger(__name__)

ClassifyFn = Callable[[EmailInput], ClassifierResult]
ExplainFn = Callable[
    [RiskAssessment, EmailInput, list[Indicator]], explainer.Explanation
]


class AnalysisError(Exception):
    """A fatal analysis failure with a message that can be shown to the user."""


@contextmanager
def _timed(stage: str) -> Iterator[None]:
    """Log how long a stage took (no email content)."""
    start = time.perf_counter()
    try:
        yield
    finally:
        log.info("stage=%s ms=%.0f", stage, (time.perf_counter() - start) * 1000)


def email_urls(email: EmailInput) -> list[str]:
    """Return the pasted URL followed by body links, without duplicates."""
    urls = [email.url] if email.url else []
    return urls + [u for u in email.body_urls if u not in urls]


def analyze(
    email_input: EmailInput,
    classify: ClassifyFn = classifier.classify,
    explain: ExplainFn = explainer.explain,
) -> AnalysisReport:
    """Run classifier, rules, URL checks, scoring, and explanation for one email."""
    with _timed("classify"):
        try:
            classifier_result = classify(email_input)
        except Exception as exc:  # surface any model failure clearly
            log.error("Classifier failed: %s", type(exc).__name__)
            raise AnalysisError(
                "The phishing classifier couldn't run, so no risk level is available. "
                "Check that the model is downloaded (scripts/download_models.py)."
            ) from exc
    with _timed("rules"):
        indicators = find_indicators(email_text(email_input))
    with _timed("url_checks"):
        findings = [f for url in email_urls(email_input) for f in url_findings(url)]
    with _timed("scoring"):
        assessment = assess_risk(classifier_result, indicators, findings)
    with _timed("explain"):
        try:
            explanation = explain(assessment, email_input, indicators)
        except Exception as exc:  # noqa: BLE001 - the LLM must never be fatal
            log.warning("Explainer failed: %s", type(exc).__name__)
            explanation = explainer.fallback_explanation(assessment, indicators)
    return AnalysisReport(
        email=email_input,
        classifier=classifier_result,
        indicators=indicators,
        url_findings=findings,
        assessment=assessment,
        explanation=explanation,
    )
