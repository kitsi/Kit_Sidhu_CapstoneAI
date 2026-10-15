"""Tests for URL text checks. None of these make a network request."""

import inspect

import pytest

from phish_assistant import url_checks
from phish_assistant.url_checks import url_findings

NO_HTTPS = "HTTPS"
RAW_IP = "raw IP"
PUNYCODE = "punycode"
AT_SIGN = "'@'"
SHORTENER = "shortener"
SUBDOMAINS = "subdomains"


def has(findings: list[str], marker: str) -> bool:
    """Return True if any finding mentions the marker text."""
    return any(marker in f for f in findings)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://192.168.1.5/login", {NO_HTTPS, RAW_IP}),
        ("https://xn--pypal-4ve.com", {PUNYCODE}),
        ("https://paypal.com@evil.example", {AT_SIGN}),
        ("bit.ly/abc", {SHORTENER}),
        ("https://www.example.com/account", set()),
    ],
)
def test_milestone_4_urls(url: str, expected: set[str]) -> None:
    findings = url_findings(url)
    markers = {NO_HTTPS, RAW_IP, PUNYCODE, AT_SIGN, SHORTENER, SUBDOMAINS}
    assert {m for m in markers if has(findings, m)} == expected


def test_no_https_only_flagged_when_scheme_given() -> None:
    assert not has(url_findings("example.com/login"), NO_HTTPS)
    assert has(url_findings("http://example.com/login"), NO_HTTPS)


def test_uppercase_scheme_still_checked() -> None:
    assert has(url_findings("HTTP://example.com"), NO_HTTPS)


def test_ipv6_host_flagged() -> None:
    assert has(url_findings("https://[2001:db8::1]/login"), RAW_IP)


def test_shortener_subdomain_flagged_but_lookalike_not() -> None:
    assert has(url_findings("https://www.bit.ly/x"), SHORTENER)
    assert not has(url_findings("https://notbit.ly/x"), SHORTENER)


@pytest.mark.parametrize(
    ("url", "flagged"),
    [
        ("https://accounts.example.com", False),
        ("https://www.shop.example.com", False),
        ("https://bank.secure-verify.example.com", True),
        ("https://contoso-bank.secure-verify.account-update.example/confirm", True),
    ],
)
def test_subdomain_threshold(url: str, flagged: bool) -> None:
    assert has(url_findings(url), SUBDOMAINS) is flagged


def test_malformed_url_is_a_finding_not_a_crash() -> None:
    findings = url_findings("http://[::1")
    assert len(findings) == 1
    assert "malformed" in findings[0]


def test_module_has_no_network_code() -> None:
    source = inspect.getsource(url_checks)
    for name in ("requests", "urlopen", "httpx", "socket", "urllib.request"):
        assert name not in source
