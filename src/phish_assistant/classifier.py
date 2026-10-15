"""Hugging Face classifier wrapper: load once, score email text."""

from typing import Any

from phish_assistant.config import (
    CLASSIFIER_MAX_TOKENS,
    CLASSIFIER_MODEL_ID,
    PHISHING_LABEL,
)
from phish_assistant.models import ClassifierResult, EmailInput

_classifier: Any = None  # loaded on first use, then reused


def _get_classifier() -> Any:
    """Return the text-classification pipeline, loading it on first call."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline

            _classifier = pipeline(
                "text-classification", model=CLASSIFIER_MODEL_ID, top_k=None
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not load the classifier '{CLASSIFIER_MODEL_ID}'. "
                "Run scripts/download_models.py while online, then try again."
            ) from exc
    return _classifier


def email_text(email: EmailInput) -> str:
    """Combine subject and body into the text the classifier sees."""
    return f"{email.subject}\n\n{email.body}" if email.subject else email.body


def phishing_probability(scores: dict[str, float]) -> float:
    """Return the probability that email text is phishing, from raw label scores."""
    return scores.get(PHISHING_LABEL, 0.0)


def _is_truncated(classifier: Any, text: str) -> bool:
    """Return True if `text` is longer than the model's token limit."""
    token_ids = classifier.tokenizer(text, verbose=False)["input_ids"]
    return len(token_ids) > CLASSIFIER_MAX_TOKENS


def classify(email: EmailInput) -> ClassifierResult:
    """Score an email's subject and body. URLs are not sent to the model."""
    classifier = _get_classifier()
    text = email_text(email)
    results = classifier(text, truncation=True, max_length=CLASSIFIER_MAX_TOKENS)
    if results and isinstance(results[0], list):  # some versions nest one level deeper
        results = results[0]
    scores = {r["label"]: float(r["score"]) for r in results}
    return ClassifierResult(
        label_scores=scores,
        phishing_probability=phishing_probability(scores),
        truncated=_is_truncated(classifier, text),
    )
