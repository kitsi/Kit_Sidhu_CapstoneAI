"""Model names, thresholds, and limits in one place."""

CLASSIFIER_MODEL_ID = "cybersectony/phishing-email-detection-distilbert_v2.4.1"
OLLAMA_MODEL = "llama3.2:3b"

# Classifier label mapping, decided from scripts/explore_classifier.py output:
# on email text LABEL_0 tracks legitimate and LABEL_1 tracks phishing. URLs are
# not classified by the model (every URL scored LABEL_3 = 1.0); url_checks.py
# handles them instead.
PHISHING_LABEL = "LABEL_1"
CLASSIFIER_MAX_TOKENS = 512

# Input limits, enforced by validation.py.
MAX_SUBJECT_CHARS = 500
MAX_BODY_CHARS = 10_000
MAX_URL_CHARS = 2_048

# Points each indicator category contributes to the risk score (scoring.py).
# Requests for credentials or money are the core of a phishing attack, so they
# weigh most; pressure tactics next; generic suspicious wording least.
CATEGORY_WEIGHTS = {
    "credential_request": 3,
    "payment_request": 3,
    "threat": 2,
    "urgency": 2,
    "suspicious_language": 1,
}

