"""URL text heuristics (no network). Nothing here may open or resolve a link."""

import ipaddress
from urllib.parse import SplitResult, urlsplit

from phish_assistant.config import MAX_SUBDOMAINS, URL_SHORTENERS


def _split(url: str) -> tuple[SplitResult, bool]:
    """Split URL text into parts; a missing scheme gets "//" so the host is found."""
    had_scheme = "://" in url
    return urlsplit(url if had_scheme else "//" + url), had_scheme


def _is_ip(host: str) -> bool:
    """Return True if host is a raw IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_shortener(host: str) -> bool:
    """Return True if host is a known URL shortener or a subdomain of one."""
    return any(host == s or host.endswith("." + s) for s in URL_SHORTENERS)


def _subdomain_count(host: str) -> int:
    """Count labels before the registered domain, ignoring a leading "www."."""
    labels = host.removeprefix("www.").split(".")
    return max(0, len(labels) - 2)


def url_findings(url: str) -> list[str]:
    """Inspect URL *text* and return plain-language findings.

    Malformed URLs produce a finding instead of raising.
    """
    try:
        parts, had_scheme = _split(url.strip())
        host = (parts.hostname or "").rstrip(".")
    except ValueError:
        return ["Link is malformed and couldn't be read, which is unusual for a real link."]
    findings: list[str] = []
    if had_scheme and parts.scheme.lower() == "http":
        findings.append("Link does not use HTTPS.")
    if parts.username is not None:
        findings.append(
            "Link contains an '@' sign: the text before it is ignored and the "
            "browser goes to the address after it."
        )
    if _is_ip(host):
        findings.append("Link points to a raw IP address instead of a domain name.")
        return findings  # domain-name checks don't apply to an IP address
    if host.startswith("xn--") or ".xn--" in host:
        findings.append("Domain uses punycode, which can disguise look-alike characters.")
    if _is_shortener(host):
        findings.append("Link uses a URL shortener, which hides the real destination.")
    if _subdomain_count(host) > MAX_SUBDOMAINS:
        findings.append(
            "Domain has an unusual number of subdomains, a common way to make a "
            "fake address look official."
        )
    return findings
