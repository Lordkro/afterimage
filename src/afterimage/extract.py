from __future__ import annotations

import re
from html.parser import HTMLParser

_SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "template",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "button",
}
_MAIN_TAGS = {"main", "article"}
_CHROME_LINE = re.compile(
    r"^(skip to (main )?content|deploy on fastapi cloud|follow @\S+ on.*)$",
    re.I,
)
_SKIP_ROLES = {"banner", "navigation", "contentinfo", "complementary", "search"}


def _attr(attrs: list[tuple[str, str | None]], name: str) -> str:
    for key, value in attrs:
        if key.lower() == name and value:
            return value.lower()
    return ""


class _ReadableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.main_parts: list[str] = []
        self._skip_depth = 0
        self._main_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        role = _attr(attrs, "role")
        if self._skip_depth or tag in _SKIP_TAGS or role in _SKIP_ROLES:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag in _MAIN_TAGS:
            self._main_depth += 1
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "li", "br", "tr", "section"}:
            bucket = self.main_parts if self._main_depth else self.body_parts
            bucket.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag in _MAIN_TAGS and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        bucket = self.main_parts if self._main_depth else self.body_parts
        bucket.append(data)


def extract_readable(body: bytes, content_type: str = "text/html") -> tuple[str, str]:
    """Return (title, readable text). Never returns raw markup."""
    charset = _charset(content_type)
    html = body.decode(charset, errors="replace")
    parser = _ReadableParser()
    parser.feed(html)
    parser.close()
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    raw = parser.main_parts if "".join(parser.main_parts).strip() else parser.body_parts
    text = re.sub(r"[ \t]+", " ", "".join(raw))
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not _CHROME_LINE.match(line)]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return title, text


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    return match.group(1) if match else "utf-8"
