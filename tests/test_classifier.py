"""Tests for the classifier wrapper. The real-model test is skipped if it isn't cached."""

import pytest
from huggingface_hub import try_to_load_from_cache

from phish_assistant import classifier
from phish_assistant.config import CLASSIFIER_MODEL_ID, PHISHING_LABEL
from phish_assistant.models import EmailInput

MODEL_CACHED = isinstance(try_to_load_from_cache(CLASSIFIER_MODEL_ID, "config.json"), str)


def test_phishing_probability_uses_mapped_label() -> None:
    scores = {"LABEL_0": 0.1, PHISHING_LABEL: 0.7, "LABEL_2": 0.05, "LABEL_3": 0.15}
    assert classifier.phishing_probability(scores) == 0.7


def test_phishing_probability_missing_label_is_zero() -> None:
    assert classifier.phishing_probability({"LABEL_0": 1.0}) == 0.0


def test_email_text_combines_subject_and_body() -> None:
    assert classifier.email_text(EmailInput("Subj", "Body")) == "Subj\n\nBody"
    assert classifier.email_text(EmailInput("", "Body")) == "Body"


@pytest.mark.skipif(not MODEL_CACHED, reason="classifier model not downloaded")
def test_real_model_scores_phishing_higher_than_legitimate() -> None:
    phish = classifier.classify(
        EmailInput(
            "Urgent: account suspended",
            "Your account will be suspended in 24 hours. Verify your password "
            "immediately at the link below to avoid losing access.",
        )
    )
    legit = classifier.classify(
        EmailInput("Team meeting", "Reminder: our weekly sync is Thursday at 10am in room 4.")
    )
    assert abs(sum(phish.label_scores.values()) - 1.0) < 1e-3
    assert 0.0 <= phish.phishing_probability <= 1.0
    assert phish.phishing_probability > legit.phishing_probability
    assert phish.truncated is False


@pytest.mark.skipif(not MODEL_CACHED, reason="classifier model not downloaded")
def test_real_model_flags_truncation() -> None:
    result = classifier.classify(EmailInput("Long", "word " * 1000))
    assert result.truncated is True
