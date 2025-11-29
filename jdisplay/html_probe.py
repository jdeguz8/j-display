"""Small helper to probe an HTML page and grab its <title>.

This is only used during development to verify that we can reach
the Environment Canada site successfully.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen


class _TitleParser(HTMLParser):
    """Very small HTML parser that extracts only the first <title> tag."""

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title: Optional[str] = None

    def handle_starttag(self, tag, attrs):  # noqa: D401 (docstring not needed)
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()


def fetch_title(url: str) -> Optional[str]:
    """Return the <title> text from the given URL, or None on error."""
    try:
        # nosec B310: this is a simple read-only probe to a trusted URL.
        with urlopen(url, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except URLError:
        return None

    parser = _TitleParser()
    parser.feed(html)
    return parser.title
