"""Input cleaning and validation. URLs are handled as text and never fetched."""

import ipaddress
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from phish_assistant.config import MAX_BODY_CHARS, MAX_SUBJECT_CHARS, MAX_URL_CHARS
from phish_assistant.models import EmailInput

_URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)
_TRAILING_PUNCTUATION = ".,;:!?)]}'\""
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


class _TextExtractor(HTMLParser):
    """Collect visible text and link targets; drop tags, scripts, and styles."""

    _SKIP_TAGS = frozenset({"script", "style"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hrefs: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "a":
            self.hrefs.extend(value for name, value in attrs if name == "href" and value)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def strip_html(body: str) -> tuple[str, list[str]]:
    """Return (plain text, link targets). Plain-text bodies are returned unchanged."""
    if not _HTML_TAG.search(body):
        return body, []
    parser = _TextExtractor()
    parser.feed(body)
    parser.close()
    text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip(), parser.hrefs


def extract_urls(text: str) -> list[str]:
    """Find http(s):// and www. links in text, in order, without duplicates."""
    urls: list[str] = []
    for match in _URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        if url not in urls:
            urls.append(url)
    return urls


def looks_like_url(url: str) -> bool:
    """Return True if the text has the shape of a web address (string check only)."""
    if any(ch.isspace() for ch in url):
        return False
    try:
        parts = urlsplit(url if "://" in url else "//" + url)
        host = parts.hostname or ""
    except ValueError:
        return False
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return "." in host.strip(".")


def validate_input(subject: str, body: str, url: str = "") -> EmailInput:
    """Clean raw form values and reject input the pipeline can't analyze."""
    subject, body, url = subject.strip(), body.strip(), url.strip()
    if len(subject) > MAX_SUBJECT_CHARS:
        raise ValueError(f"The subject is longer than {MAX_SUBJECT_CHARS:,} characters.")
    if not body:
        raise ValueError("Paste the email message you want to analyze.")
    if len(body) > MAX_BODY_CHARS:
        raise ValueError(
            f"The message is longer than {MAX_BODY_CHARS:,} characters. "
            "Paste a shorter excerpt."
        )
    if url and (len(url) > MAX_URL_CHARS or not looks_like_url(url)):
        raise ValueError(
            "The link doesn't look like a web address. "
            "Paste it as text, for example https://example.com/login."
        )
    body, hrefs = strip_html(body)
    if not body:
        raise ValueError("The message has no readable text after removing HTML.")
    body_urls = extract_urls(body)
    body_urls += [
        h for h in hrefs if h not in body_urls and _URL_PATTERN.match(h) and looks_like_url(h)
    ]
    return EmailInput(subject=subject, body=body, url=url or None, body_urls=body_urls)
