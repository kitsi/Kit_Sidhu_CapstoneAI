"""Run the classifier on every eval sample and print a table of raw label scores.

Exploration for Milestone 1: no label mapping is assumed here. URLs are passed to
the classifier as plain text and are never fetched.
"""

import json
import time
from pathlib import Path

from transformers import pipeline
from transformers.utils import logging as hf_logging

from phish_assistant.config import CLASSIFIER_MODEL_ID

EVAL_SET = Path(__file__).resolve().parent.parent / "eval" / "eval_set.jsonl"


def load_samples(path: Path) -> list[dict]:
    """Read one JSON object per non-empty line."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def score(classifier, text: str) -> tuple[dict[str, float], float]:
    """Return every label's score for `text` and the inference time in milliseconds."""
    start = time.perf_counter()
    results = classifier(text, truncation=True, max_length=512)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if results and isinstance(results[0], list):  # some versions nest one level deeper
        results = results[0]
    return {r["label"]: r["score"] for r in results}, elapsed_ms


def main() -> None:
    """Score each sample's text and URL, then print one table row per input."""
    hf_logging.set_verbosity_error()
    hf_logging.disable_progress_bar()
    classifier = pipeline("text-classification", model=CLASSIFIER_MODEL_ID, top_k=None)
    labels = [
        classifier.model.config.id2label[i]
        for i in sorted(classifier.model.config.id2label)
    ]

    header = f"{'id':<34} {'input':<5} {'exp':<6} " + " ".join(
        f"{lb:>8}" for lb in labels
    )
    print(header + f" {'sum':>6} {'top':>8} {'ms':>6}")
    print("-" * len(header + " " * 23))
    for sample in load_samples(EVAL_SET):
        inputs = [("text", f"{sample['subject']}\n\n{sample['body']}")]
        if sample["url"]:
            inputs.append(("url", sample["url"]))
        for kind, text in inputs:
            scores, ms = score(classifier, text)
            cells = " ".join(f"{scores[lb]:>8.4f}" for lb in labels)
            top = max(scores, key=scores.get)
            expected = "phish" if sample["expected"] == "phishing" else "legit"
            print(
                f"{sample['id']:<34} {kind:<5} {expected:<6} {cells} "
                f"{sum(scores.values()):>6.3f} {top:>8} {ms:>6.1f}"
            )


if __name__ == "__main__":
    main()
