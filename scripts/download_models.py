"""Download the classifier into the local Hugging Face cache and print its labels."""

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from phish_assistant.config import CLASSIFIER_MODEL_ID


def main() -> None:
    """Load the tokenizer and model once so later runs read them from the cache."""
    AutoTokenizer.from_pretrained(CLASSIFIER_MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(CLASSIFIER_MODEL_ID)
    print(f"Cached: {CLASSIFIER_MODEL_ID}")
    print(f"id2label: {model.config.id2label}")


if __name__ == "__main__":
    main()
