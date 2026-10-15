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

# URL text checks (url_checks.py). Matching is on the hostname, so subdomains of
# a shortener (e.g. "www.bit.ly") also count.
URL_SHORTENERS = frozenset({
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
    "tiny.cc",
    "shorturl.at",
})
# Flag a host with more subdomains than this, not counting a leading "www.".
# "accounts.example.com" has 1; "bank.secure-verify.example.com" has 2.
MAX_SUBDOMAINS = 1

# Risk scoring (scoring.py):
#   score = CLASSIFIER_WEIGHT * phishing_probability
#         + INDICATOR_WEIGHT * min(1, indicator_points / INDICATOR_POINTS_CAP)
# Every indicator match adds its category weight (repeats count: each is
# separate evidence, and the cap stops them inflating the score). Each URL
# finding adds URL_FINDING_POINTS.
CLASSIFIER_WEIGHT = 0.6
INDICATOR_WEIGHT = 0.4
INDICATOR_POINTS_CAP = 5
URL_FINDING_POINTS = 1
MEDIUM_THRESHOLD = 0.35  # score >= this is at least Medium
HIGH_THRESHOLD = 0.65  # score >= this is High
