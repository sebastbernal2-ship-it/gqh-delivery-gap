"""HTML to text for filing documents, plus a bounded, deterministic excerpt.

The cache holds raw HTML. Extraction must be deterministic and stdlib-only so any reader can
reproduce the context a model saw from the same bytes.
"""
from __future__ import annotations

import hashlib
import re
from html import unescape
from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "head", "noscript"}
BREAK_TAGS = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table"}
DEFAULT_FOCUS = ("Item 1.01", "Item 2.02", "Item 7.01", "Item 8.01")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self.skipping += 1
        elif tag in BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self.skipping:
            self.skipping -= 1
        elif tag in BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipping:
            self.parts.append(data)

    def text(self) -> str:
        raw = unescape("".join(self.parts)).replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def excerpt(text: str, max_chars: int = 4000, focus: tuple[str, ...] = DEFAULT_FOCUS) -> str:
    """A bounded window that prefers the first declared item heading, else the head.

    The excerpt is the model context, so it never reads past ``max_chars`` and prefers the
    disclosure items over cover-page boilerplate.
    """
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    for term in focus:
        index = text.find(term)
        if index >= 0:
            start = max(0, index - 200)
            return text[start:start + max_chars]
    return text[:max_chars]


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
