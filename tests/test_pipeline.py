"""End-to-end pipeline tests with a stubbed classifier and LLM (no models loaded)."""

import logging

import pytest

from phish_assistant.explainer import Explanation
from phish_assistant.models import ClassifierResult, EmailInput
from phish_assistant.pipeline import AnalysisError, analyze, email_urls

PHISH = EmailInput(
    subject="Action required",
    body="Verify your identity immediately or your account will be suspended. "
    "Details: https://bit.ly/x",
    url="http://192.168.4.2/login",
    body_urls=["https://bit.ly/x"],
)
LEGIT = EmailInput("Team sync", "Our weekly sync is tomorrow at 10:00 in Room 3B.")


def stub_classify(p: float):
    """Return a classify function that always gives probability p."""
    return lambda email: ClassifierResult({"LABEL_1": p}, p, truncated=False)


def stub_explain(assessment, email, indicators) -> Explanation:
    """A fixed, valid explanation."""
    return Explanation(
        summary=f"Rated {assessment.level}.",
        evidence=[],
        recommended_actions=["Report it."],
        limitations="Automated.",
    )


def test_phishing_email_full_report() -> None:
    report = analyze(PHISH, classify=stub_classify(0.95), explain=stub_explain)
    assert report.assessment.level == "High"
    assert {i.category for i in report.indicators} >= {
        "urgency",
        "credential_request",
        "threat",
    }
    assert any("raw IP" in f for f in report.url_findings)  # pasted URL
    assert any("shortener" in f for f in report.url_findings)  # body URL
    assert report.explanation.summary == "Rated High."
    assert report.explanation.is_fallback is False


def test_legitimate_email_is_low() -> None:
    report = analyze(LEGIT, classify=stub_classify(0.02), explain=stub_explain)
    assert report.assessment.level == "Low"
    assert report.indicators == [] and report.url_findings == []


def test_classifier_failure_is_fatal_with_clear_message() -> None:
    def broken(email):
        raise RuntimeError("model missing")

    with pytest.raises(AnalysisError, match="classifier couldn't run"):
        analyze(PHISH, classify=broken, explain=stub_explain)


def test_explainer_failure_degrades_to_fallback() -> None:
    def broken(assessment, email, indicators):
        raise ConnectionError("Ollama down")

    report = analyze(PHISH, classify=stub_classify(0.95), explain=broken)
    assert report.assessment.level == "High"
    assert report.explanation.is_fallback is True


def test_logs_timings_but_never_email_content(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="phish_assistant"):
        analyze(PHISH, classify=stub_classify(0.95), explain=stub_explain)
    logged = caplog.text
    assert "stage=classify" in logged and "stage=explain" in logged
    for secret in ("Verify your identity", "192.168.4.2", "bit.ly", "Action required"):
        assert secret not in logged


def test_email_urls_dedupes_pasted_and_body_links() -> None:
    email = EmailInput(
        "s",
        "b",
        url="https://a.example",
        body_urls=["https://a.example", "https://b.example"],
    )
    assert email_urls(email) == ["https://a.example", "https://b.example"]
