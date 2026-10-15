"""Tests for input cleaning, validation, and URL extraction."""

import pytest

from phish_assistant.config import MAX_BODY_CHARS, MAX_SUBJECT_CHARS
from phish_assistant.validation import (
    extract_urls,
    looks_like_url,
    strip_html,
    validate_input,
)


def test_empty_body_rejected() -> None:
    with pytest.raises(ValueError, match="Paste the email"):
        validate_input("Hi", "")


def test_whitespace_only_body_rejected() -> None:
    with pytest.raises(ValueError, match="Paste the email"):
        validate_input("Hi", "   \n\t  ")


def test_body_one_char_over_limit_rejected() -> None:
    with pytest.raises(ValueError, match="longer than"):
        validate_input("Hi", "a" * (MAX_BODY_CHARS + 1))


def test_body_at_limit_accepted() -> None:
    assert len(validate_input("Hi", "a" * MAX_BODY_CHARS).body) == MAX_BODY_CHARS


def test_oversized_subject_rejected() -> None:
    with pytest.raises(ValueError, match="subject"):
        validate_input("s" * (MAX_SUBJECT_CHARS + 1), "body")


def test_valid_input_without_url() -> None:
    email = validate_input("  Lunch?  ", "  Want to grab lunch at noon?  ")
    assert email.subject == "Lunch?"
    assert email.body == "Want to grab lunch at noon?"
    assert email.url is None
    assert email.body_urls == []


def test_valid_url_kept() -> None:
    email = validate_input("Hi", "Body", " https://example.com/login ")
    assert email.url == "https://example.com/login"


@pytest.mark.parametrize("bad_url", ["not a url", "hello", "javascript:alert(1)", "http://"])
def test_non_url_rejected(bad_url: str) -> None:
    with pytest.raises(ValueError, match="web address"):
        validate_input("Hi", "Body", bad_url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "bit.ly/abc",
        "http://192.168.1.5/login",
        "https://xn--pypal-4ve.com",
        "https://paypal.com@evil.example",
    ],
)
def test_looks_like_url_accepts_suspicious_but_valid_shapes(url: str) -> None:
    assert looks_like_url(url)


def test_html_tags_stripped_and_href_extracted() -> None:
    body = '<p>Click <a href="http://evil.example/login">here</a> now</p>'
    email = validate_input("Hi", body)
    assert email.body == "Click here now"
    assert email.body_urls == ["http://evil.example/login"]


def test_script_content_dropped() -> None:
    text, _ = strip_html("<p>Hello</p><script>alert(1)</script>")
    assert text == "Hello"


def test_html_only_body_rejected() -> None:
    with pytest.raises(ValueError, match="no readable text"):
        validate_input("Hi", "<div><br></div>")


def test_plain_text_with_angle_bracket_unchanged() -> None:
    assert strip_html("if a < b then pay")[0] == "if a < b then pay"


def test_extract_urls_trims_punctuation_and_dedupes() -> None:
    text = "Go to https://a.example/x. Also www.b.example, then https://a.example/x!"
    assert extract_urls(text) == ["https://a.example/x", "www.b.example"]


def test_extract_urls_none_found() -> None:
    assert extract_urls("No links here, just contact the help desk.") == []
