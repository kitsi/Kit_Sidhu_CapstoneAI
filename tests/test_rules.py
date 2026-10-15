"""Tests for social-engineering indicator detection."""

import pytest

from phish_assistant.config import CATEGORY_WEIGHTS
from phish_assistant.rules import PATTERNS, find_indicators


def categories(text: str) -> set[str]:
    """Return the set of categories found in text."""
    return {i.category for i in find_indicators(text)}


@pytest.mark.parametrize(
    ("category", "positive", "negative"),
    [
        ("urgency", "Please act now to keep access.", "Please contact now-retired staff."),
        ("urgency", "Reply within 24 hours.", "Your order ships within 2 business days."),
        ("threat", "Your account will be suspended.", "Your password will stay the same."),
        ("threat", "This may lead to legal action.", "The legal team approved the action plan."),
        (
            "credential_request",
            "Enter your username and password below.",
            "We received a request to reset your password.",
        ),
        (
            "payment_request",
            "Buy five Apple gift cards for a client.",
            "Your order total is $103.00.",
        ),
        (
            "payment_request",
            "Send payment by wire transfer to our new bank account.",
            "Your payment was received, thank you.",
        ),
        (
            "suspicious_language",
            "Dear user, we noticed unusual sign-in activity.",
            "Dear Priya, see you at the sync.",
        ),
    ],
)
def test_category_positive_and_negative(category: str, positive: str, negative: str) -> None:
    assert category in categories(positive)
    assert category not in categories(negative)


def test_every_category_has_a_weight() -> None:
    assert set(PATTERNS) == set(CATEGORY_WEIGHTS)


def test_matching_is_case_insensitive() -> None:
    assert "urgency" in categories("ACT NOW OR LOSE ACCESS")


def test_offsets_point_at_matched_text() -> None:
    text = "Hi, please verify your identity immediately."
    for indicator in find_indicators(text):
        assert text[indicator.start : indicator.end] == indicator.matched


def test_overlapping_matches_in_same_category_counted_once() -> None:
    # "enter your username" and "username and password" overlap; keep one.
    found = find_indicators("Enter your username and password.")
    credential = [i for i in found if i.category == "credential_request"]
    assert len(credential) == 1
    assert credential[0].matched == "Enter your username"


def test_overlaps_across_categories_are_kept() -> None:
    # "confirm your details now" is both urgency and a credential request.
    assert categories("Confirm your details now.") == {"urgency", "credential_request"}


def test_results_sorted_by_position() -> None:
    found = find_indicators("Act now. Dear customer, buy a gift card. Legal action follows.")
    assert [i.start for i in found] == sorted(i.start for i in found)


def test_ordinary_email_has_no_indicators() -> None:
    text = "Hi team, the weekly sync is tomorrow at 10:00. Add agenda items to the doc."
    assert find_indicators(text) == []
