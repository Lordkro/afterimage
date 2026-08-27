from __future__ import annotations

import re
from html.parser import HTMLParser


class _ReadableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._skip_depth += 1
            return
        if tag == "title" and self._skip_depth == 0:
            self._in_title = True
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "li", "br", "tr", "section"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        self.text_parts.append(data)


def extract_readable(body: bytes, content_type: str = "text/html") -> tuple[str, str]:
    """Return (title, readable text). Never returns raw markup."""
    charset = _charset(content_type)
    html = body.decode(charset, errors="replace")
    parser = _ReadableParser()
    parser.feed(html)
    parser.close()
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    text = re.sub(r"[ \t]+", " ", "".join(parser.text_parts))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    return match.group(1) if match else "utf-8"
