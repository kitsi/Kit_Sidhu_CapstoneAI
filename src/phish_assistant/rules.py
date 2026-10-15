"""Social-engineering indicator patterns."""

import re

from phish_assistant.models import Indicator


def _compile(*patterns: str) -> list[re.Pattern[str]]:
    """Compile case-insensitive patterns."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Phrases drawn from the phishing samples in eval/eval_set.jsonl. Every pattern
# is bounded by \b so "act now" can't match inside "contact now".
PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "urgency": _compile(
        r"\bimmediately\b",
        r"\burgent(?:ly)?\b",
        r"\bwithin \d+ hours\b",
        r"\b(?:act|respond|reply|confirm|verify)(?: your \w+)? now\b",
        r"\b(?:final notice|action required)\b",
    ),
    "threat": _compile(
        r"\bwill be (?:permanently )?"
        r"(?:suspended|restricted|closed|terminated|deleted|locked|returned)\b",
        r"\blegal action\b",
        r"\bloss of (?:funds|access|data)\b",
        r"\bto avoid (?:suspension|late fees|service interruption|penalt(?:y|ies))\b",
        r"\bfailure to (?:confirm|verify|respond|pay)\b",
    ),
    "credential_request": _compile(
        r"\bverify your (?:identity|account|login|details|information)\b",
        r"\b(?:enter|confirm|provide|update) your "
        r"(?:username|password|login|credentials|(?:account |banking )?details)\b",
        r"\busername and password\b",
        r"\blogin credentials\b",
    ),
    "payment_request": _compile(
        r"\bgift ?cards?\b",
        r"\bwire transfer\b",
        r"\b(?:new|updated) bank(?:ing)? (?:account|details)\b",
        r"\b(?:arrange|make|send) (?:a |the )?payment\b",
        r"\bfee of \$\d[\d,.]*",
        r"\bpay (?:the|a) fee\b",
    ),
    "suspicious_language": _compile(
        r"\bdear (?:user|customer|client|member|account holder)\b",
        r"\bkeep this (?:confidential|between us|quiet)\b",
        r"\bclick (?:the|this) link\b",
        r"\b(?:unusual|suspicious) (?:sign[- ]in|login|activity)\b",
        r"\bare you at your desk\b",
        r"\bsecure document\b",
    ),
}


def _all_matches(text: str) -> list[Indicator]:
    """Return every pattern match in text, before overlap handling."""
    return [
        Indicator(category, m.group(0), m.start(), m.end())
        for category, patterns in PATTERNS.items()
        for pattern in patterns
        for m in pattern.finditer(text)
    ]


def _overlaps(a: Indicator, b: Indicator) -> bool:
    """Return True if two indicators share at least one character."""
    return a.start < b.end and b.start < a.end


def find_indicators(text: str) -> list[Indicator]:
    """Find social-engineering phrases in text, sorted by position.

    Overlapping matches in the same category keep only the earliest, longest
    one, so one phrase isn't counted twice. Overlaps across categories are kept,
    because the same words can be both urgent and a credential request.
    """
    candidates = sorted(_all_matches(text), key=lambda i: (i.start, -(i.end - i.start)))
    kept: list[Indicator] = []
    for candidate in candidates:
        if not any(k.category == candidate.category and _overlaps(k, candidate) for k in kept):
            kept.append(candidate)
    return kept
