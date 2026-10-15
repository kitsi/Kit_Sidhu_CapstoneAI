"""Run the analyzer (no LLM) on every eval sample and compare with the expected label.

A phishing sample counts as correct at Medium or High; a legitimate sample only
at Low. Prints sample ids and reasons, never the email text itself.
"""

import json
from collections import Counter
from pathlib import Path

from transformers.utils import logging as hf_logging

from phish_assistant.classifier import classify, email_text
from phish_assistant.models import EmailInput, RiskAssessment
from phish_assistant.rules import find_indicators
from phish_assistant.scoring import LEVELS, assess_risk
from phish_assistant.url_checks import url_findings
from phish_assistant.validation import validate_input

EVAL_SET = Path(__file__).resolve().parent / "eval_set.jsonl"
CORRECT_LEVELS = {"phishing": {"Medium", "High"}, "legitimate": {"Low"}}


def load_samples(path: Path) -> list[dict]:
    """Read one JSON object per non-empty line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def analyze(email: EmailInput) -> RiskAssessment:
    """Classifier + rules + URL checks + scoring for one email."""
    urls = ([email.url] if email.url else []) + email.body_urls
    findings = [f for url in urls for f in url_findings(url)]
    return assess_risk(classify(email), find_indicators(email_text(email)), findings)


def main() -> None:
    """Print one block per sample, a confusion matrix, and a summary."""
    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
    matrix: Counter[tuple[str, str]] = Counter()
    misses = []
    for sample in load_samples(EVAL_SET):
        email = validate_input(sample["subject"], sample["body"], sample["url"] or "")
        assessment = analyze(email)
        expected = sample["expected"]
        ok = assessment.level in CORRECT_LEVELS[expected]
        matrix[(expected, assessment.level)] += 1
        if not ok:
            misses.append(sample["id"])
        mark = "ok  " if ok else "MISS"
        print(
            f"{mark} {sample['id']:<34} expected {expected:<10} "
            f"-> {assessment.level:<6} (score {assessment.score:.2f})"
        )
        for reason in assessment.reasons:
            print(f"       - {reason}")

    print("\nConfusion matrix (rows: expected, columns: predicted level)")
    print(f"{'':<12}" + "".join(f"{lv:>8}" for lv in LEVELS))
    for expected in CORRECT_LEVELS:
        print(
            f"{expected:<12}" + "".join(f"{matrix[(expected, lv)]:>8}" for lv in LEVELS)
        )
    total = sum(matrix.values())
    print(f"\nCorrect: {total - len(misses)}/{total}")
    if misses:
        print("Misclassified: " + ", ".join(misses))


if __name__ == "__main__":
    main()
