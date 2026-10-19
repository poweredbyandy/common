"""Markdown → HTML for the document body editor."""

from __future__ import annotations

import html
import logging
import re

_logger = logging.getLogger(__name__)

try:
    import markdown as md_lib
except ImportError:
    md_lib = None
    _logger.debug("Cannot import markdown.")

_MD_EXTENSIONS = [
    "extra",
    "sane_lists",
    "nl2br",
    "tables",
    "fenced_code",
]


def markdown_to_html(text):
    """Convert Markdown to rich HTML (not raw Markdown)."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if md_lib is not None:
        return md_lib.markdown(text, extensions=_MD_EXTENSIONS)
    return _fallback_markdown_to_html(text)


_RE_FENCE = re.compile(
    r"^```([a-zA-Z0-9_-]*)\n(.*?)\n```\s*$",
    re.DOTALL | re.MULTILINE,
)
_RE_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
_RE_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_RE_UL = re.compile(r"^(\s*)([-*+])\s+(.+)$")
_RE_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.+)$")
_RE_BQ = re.compile(r"^>\s?(.*)$")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_CODE = re.compile(r"`([^`]+)`")
_RE_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_RE_ITALIC = re.compile(
    r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)"
)


def _fallback_markdown_to_html(text):
    blocks = []
    pos = 0
    for match in _RE_FENCE.finditer(text):
        if match.start() > pos:
            blocks.extend(_parse_blocks(text[pos : match.start()]))
        code = match.group(2)
        blocks.append("<pre><code>%s</code></pre>" % html.escape(code))
        pos = match.end()
    if pos < len(text):
        blocks.extend(_parse_blocks(text[pos:]))
    return "\n".join(block for block in blocks if block)


def _parse_blocks(text):
    lines = text.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if _RE_HR.match(stripped):
            blocks.append("<hr/>")
            i += 1
            continue
        heading = _RE_HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            blocks.append(
                "<h%s>%s</h%s>"
                % (level, _inline(heading.group(2).strip()), level)
            )
            i += 1
            continue
        if _RE_BQ.match(line):
            quote_lines = []
            while i < len(lines):
                bq = _RE_BQ.match(lines[i])
                if not bq:
                    break
                quote_lines.append(bq.group(1))
                i += 1
            inner = _inline(" ".join(quote_lines).strip())
            blocks.append("<blockquote><p>%s</p></blockquote>" % inner)
            continue
        if _RE_UL.match(line) or _RE_OL.match(line):
            list_html, i = _parse_list(lines, i)
            blocks.append(list_html)
            continue
        para = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip():
                break
            if (
                _RE_HR.match(nxt.strip())
                or _RE_HEADING.match(nxt)
                or _RE_BQ.match(nxt)
                or _RE_UL.match(nxt)
                or _RE_OL.match(nxt)
            ):
                break
            para.append(nxt)
            i += 1
        content = _inline(" ".join(part.strip() for part in para))
        blocks.append("<p>%s</p>" % content)
    return blocks


def _parse_list(lines, start):
    ordered = bool(_RE_OL.match(lines[start]))
    tag = "ol" if ordered else "ul"
    items = []
    i = start
    while i < len(lines):
        match = (_RE_OL if ordered else _RE_UL).match(lines[i])
        if not match:
            break
        items.append("<li>%s</li>" % _inline(match.group(3).strip()))
        i += 1
    return "<%s>%s</%s>" % (tag, "".join(items), tag), i


def _inline(text):
    text = html.escape(text)

    def _img(match):
        return '<img src="%s" alt="%s"/>' % (match.group(2), match.group(1))

    def _link(match):
        return '<a href="%s">%s</a>' % (match.group(2), match.group(1))

    text = _RE_IMG.sub(_img, text)
    text = _RE_LINK.sub(_link, text)
    text = _RE_CODE.sub(lambda m: "<code>%s</code>" % m.group(1), text)
    text = _RE_BOLD.sub(lambda m: "<strong>%s</strong>" % m.group(2), text)
    text = _RE_ITALIC.sub(
        lambda m: "<em>%s</em>" % (m.group(1) or m.group(2)), text
    )
    return text
