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


_ALWAYS_SKIP = {"script", "style", "noscript", "svg", "template"}
_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_JS_SHELL = re.compile(
    r"uh oh! there was an error while loading|please enable javascript|"
    r"you need to enable javascript to run this app|enable js to use this",
    re.I,
)
_CHALLENGE = re.compile(
    r"verifying you are human|just a moment\.\.\.|attention required|"
    r"checking your browser before accessing|enable javascript and cookies to continue|"
    r"why do i have to complete a captcha|cloudflare ray id|"
    r"cf-browser-verification|cf-challenge|cf-turnstile|"
    r"sorry, you have been blocked",
    re.I,
)


class _ReadableParser(HTMLParser):
    def __init__(self, *, skip_chrome: bool = True) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.main_parts: list[str] = []
        self.article_parts: list[str] = []
        self._skip_depth = 0
        self._main_depth = 0
        self._article_depth = 0
        self._in_title = False
        self._skip_chrome = skip_chrome
        self._main_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        role = _attr(attrs, "role")
        skip_tags = _SKIP_TAGS if self._skip_chrome else _ALWAYS_SKIP
        skip_roles = _SKIP_ROLES if self._skip_chrome else set()
        if self._skip_depth or tag in skip_tags or role in skip_roles:
            if tag not in _VOID_TAGS:
                self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        cls = _attr(attrs, "class")
        if tag == "article":
            self._article_depth += 1
        if tag in _MAIN_TAGS:
            self._main_stack.append("main")
            self._main_depth += 1
        elif tag == "div" and ("md-content" in cls or "md-typeset" in cls):
            self._main_stack.append("md")
            self._main_depth += 1
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "li", "br", "tr", "section"}:
            self._bucket().append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if not self._main_stack:
            return
        top = self._main_stack[-1]
        if tag in _MAIN_TAGS and top == "main":
            self._main_stack.pop()
            self._main_depth -= 1
        elif tag == "div" and top == "md":
            self._main_stack.pop()
            self._main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        self._bucket().append(data)

    def _bucket(self) -> list[str]:
        if self._article_depth:
            return self.article_parts
        if self._main_depth:
            return self.main_parts
        return self.body_parts


def extract_readable(body: bytes, content_type: str = "text/html") -> tuple[str, str]:
    """Return (title, readable text). Never returns raw markup."""
    charset = _charset(content_type)
    html = body.decode(charset, errors="replace")
    title, text = _parse(html, skip_chrome=True)
    if unusable_extract(title, text, body_len=len(body)):
        title2, text2 = _parse(html, skip_chrome=False)
        if len(text2) > len(text):
            title = title or title2
            text = text2
    return title, text


def unusable_extract(title: str, text: str, *, body_len: int = 0) -> bool:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return True
    if _JS_SHELL.search(compact):
        return True
    if title and compact.lower() == title.lower():
        return True
    if body_len >= 40_000 and len(compact) < 120:
        return True
    return False


def is_challenge_page(title: str, text: str, body: bytes = b"") -> bool:
    haystack = f"{title}\n{text}\n{body.decode('utf-8', errors='replace')}"
    return bool(_CHALLENGE.search(haystack))


def worse_extract(previous: str, new: str) -> bool:
    if len(previous) < 80:
        return False
    return len(new) * 10 < len(previous)


def _parse(html: str, *, skip_chrome: bool) -> tuple[str, str]:
    parser = _ReadableParser(skip_chrome=skip_chrome)
    parser.feed(html)
    parser.close()
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    if "".join(parser.article_parts).strip():
        raw = parser.article_parts
    elif "".join(parser.main_parts).strip():
        raw = parser.main_parts
    else:
        raw = parser.body_parts
    text = re.sub(r"[ \t]+", " ", "".join(raw))
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not _CHROME_LINE.match(line)]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return title, text


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    return match.group(1) if match else "utf-8"
