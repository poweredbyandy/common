"""DOCX (Word / Google Docs) → HTML preserving table borders and cell shading."""

from __future__ import annotations

import base64
import io
import logging
import re
import zipfile
from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
V_NS = "urn:schemas-microsoft-com:vml"
NS = {"w": W_NS, "r": R_NS, "a": A_NS, "wp": WP_NS, "v": V_NS}

HEADER_FILL = "1B2A4A"
HEADER_FILL_ALT = ("1A2744", "0D2137", "1B2A4A", "002060", "1F4E79", "2F5496")


def docx_to_html(raw_bytes):
    """Convert .docx to HTML with visual fidelity for form-like tables."""
    if not raw_bytes:
        return ""
    try:
        return _ooxml_to_html(raw_bytes)
    except Exception:
        _logger.exception("OOXML DOCX convert failed; trying mammoth fallback")
        return _mammoth_fallback(raw_bytes)


def _mammoth_fallback(raw_bytes):
    try:
        import mammoth
    except ImportError as err:
        raise ImportError(
            "The Python package 'mammoth' is required to import DOCX files."
        ) from err

    def _convert_image(image):
        with image.open() as image_bytes:
            encoded = base64.b64encode(image_bytes.read()).decode("ascii")
        return {"src": "data:%s;base64,%s" % (image.content_type, encoded)}

    result = mammoth.convert_to_html(
        io.BytesIO(raw_bytes),
        convert_image=mammoth.images.img_element(_convert_image),
    )
    return _enhance_html(result.value or "")


def _ooxml_to_html(raw_bytes):
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        document_xml = zf.read("word/document.xml")
        rels = _read_rels(zf)
        media = _read_media(zf, rels)
        theme_colors = _read_theme_colors(zf)
        root = ET.fromstring(document_xml)
        body = root.find("w:body", NS)
        if body is None:
            return ""
        parts = []
        for child in list(body):
            tag = _local(child.tag)
            if tag == "tbl":
                parts.append(_table_to_html(child, media, theme_colors))
            elif tag == "p":
                parts.append(_paragraph_to_html(child, media))
        return _enhance_html("".join(parts))


def _read_theme_colors(zf):
    """Map OOXML theme color names to hex from word/theme/theme1.xml."""
    colors = {}
    candidates = (
        "word/theme/theme1.xml",
        "word/theme/theme.xml",
    )
    theme_xml = None
    for path in candidates:
        try:
            theme_xml = zf.read(path)
            break
        except KeyError:
            continue
    if not theme_xml:
        return colors
    root = ET.fromstring(theme_xml)
    names = (
        "dk1",
        "lt1",
        "dk2",
        "lt2",
        "accent1",
        "accent2",
        "accent3",
        "accent4",
        "accent5",
        "accent6",
        "hlink",
        "folHlink",
    )
    for el in root.iter():
        name = _local(el.tag)
        if name not in names:
            continue
        val = None
        for child in el.iter():
            child_name = _local(child.tag)
            if child_name == "srgbClr":
                val = child.get("val")
                break
            if child_name == "sysClr":
                val = child.get("lastClr") or child.get("val")
                break
        color = _color(val)
        if color:
            colors[name.lower()] = color
    return colors


def _read_rels(zf):
    rels = {}
    try:
        rels_xml = zf.read("word/_rels/document.xml.rels")
    except KeyError:
        return rels
    root = ET.fromstring(rels_xml)
    for rel in root:
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if rel_id and target:
            if not target.startswith("word/") and not target.startswith("/"):
                target = "word/" + target.lstrip("/")
            elif target.startswith("/"):
                target = target.lstrip("/")
            rels[rel_id] = target
    return rels


def _read_media(zf, rels):
    media = {}
    for rel_id, target in rels.items():
        if "/media/" not in target and not target.startswith("word/media/"):
            continue
        try:
            data = zf.read(target)
        except KeyError:
            try:
                data = zf.read(target.lstrip("/"))
            except KeyError:
                continue
        ext = target.rsplit(".", 1)[-1].lower()
        mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "emf": "image/emf",
            "wmf": "image/wmf",
        }.get(ext, "application/octet-stream")
        media[rel_id] = (
            "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))
        )
    return media


def _local(tag):
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _qn(tag):
    return "{%s}%s" % (W_NS, tag)


def _find(el, path):
    return el.find(path, NS)


def _findall(el, path):
    return el.findall(path, NS)


def _text_of(el):
    return "".join(el.itertext()) if el is not None else ""


def _escape(text):
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _color(val):
    if not val or val.lower() in ("auto", "nil"):
        return None
    val = val.strip().lstrip("#")
    if re.fullmatch(r"[0-9A-Fa-f]{6}", val):
        return "#" + val.upper()
    return None


def _paragraph_align(p):
    jc = _find(p, "./w:pPr/w:jc")
    if jc is None:
        return None
    val = (jc.get(_qn("val")) or "").lower()
    return {
        "center": "center",
        "right": "right",
        "both": "justify",
        "distribute": "justify",
    }.get(val)


def _run_to_html(run, media):
    texts = []
    for node in list(run):
        tag = _local(node.tag)
        if tag == "t":
            texts.append(_escape(node.text or ""))
        elif tag == "tab":
            texts.append("&emsp;")
        elif tag == "br":
            texts.append("<br/>")
        elif tag == "cr":
            texts.append("<br/>")
        elif tag == "drawing":
            img = _drawing_to_html(node, media)
            if img:
                texts.append(img)
        elif tag == "pict":
            img = _pict_to_html(node, media)
            if img:
                texts.append(img)
        elif tag == "sym":
            char = node.get(_qn("char"))
            if char:
                try:
                    texts.append("&#x%s;" % char)
                except Exception:
                    pass
    content = "".join(texts)
    if not content:
        return ""
    rpr = _find(run, "./w:rPr")
    style = []
    wrappers = []
    if rpr is not None:
        if _find(rpr, "./w:b") is not None or _find(rpr, "./w:bCs") is not None:
            wrappers.append("strong")
        if _find(rpr, "./w:i") is not None or _find(rpr, "./w:iCs") is not None:
            wrappers.append("em")
        if _find(rpr, "./w:u") is not None:
            wrappers.append("u")
        color_el = _find(rpr, "./w:color")
        if color_el is not None:
            color = _color(color_el.get(_qn("val")))
            if color:
                style.append("color:%s" % color)
        sz = _find(rpr, "./w:sz")
        if sz is not None:
            half = sz.get(_qn("val"))
            if half and half.isdigit():
                style.append("font-size:%spt" % (int(half) / 2.0))
        highlight = _find(rpr, "./w:highlight")
        if highlight is not None:
            style.append("background-color:%s" % (highlight.get(_qn("val")) or "yellow"))
    if style:
        content = '<span style="%s">%s</span>' % (";".join(style), content)
    for tag in wrappers:
        content = "<%s>%s</%s>" % (tag, content, tag)
    return content


def _drawing_to_html(drawing, media):
    blip = drawing.find(".//a:blip", NS)
    if blip is None:
        return ""
    embed = blip.get("{%s}embed" % R_NS) or blip.get("r:embed")
    src = media.get(embed)
    if not src:
        return ""
    return '<img src="%s" style="max-width:100%%;height:auto;"/>' % src


def _pict_to_html(pict, media):
    imagedata = pict.find(".//v:imagedata", NS)
    if imagedata is None:
        return ""
    rel_id = imagedata.get("{%s}id" % R_NS) or imagedata.get("r:id")
    src = media.get(rel_id)
    if not src:
        return ""
    return '<img src="%s" style="max-width:100%%;height:auto;"/>' % src


INLINE_CONTAINERS = ("hyperlink", "sdt", "sdtContent", "ins", "smartTag", "fldSimple")


def _inline_runs_to_html(parent, media):
    runs = []
    for child in list(parent):
        tag = _local(child.tag)
        if tag == "r":
            runs.append(_run_to_html(child, media))
        elif tag in INLINE_CONTAINERS:
            runs.extend(_inline_runs_to_html(child, media))
    return runs


def _paragraph_to_html(p, media, as_block=True):
    runs = _inline_runs_to_html(p, media)
    content = "".join(runs).strip()
    if not content:
        return "<p><br/></p>" if as_block else ""
    align = _paragraph_align(p)
    style = []
    if align:
        style.append("text-align:%s" % align)
    # Underlined centered titles (common in Google Docs forms)
    pstyle = _find(p, "./w:pPr/w:pStyle")
    style_name = (pstyle.get(_qn("val")) if pstyle is not None else "") or ""
    if style_name.lower() in ("title", "heading1", "heading 1"):
        tag = "h1"
    elif style_name.lower() in ("subtitle", "heading2", "heading 2"):
        tag = "h2"
    else:
        tag = "p"
    style_attr = ' style="%s"' % ";".join(style) if style else ""
    if as_block:
        return "<%s%s>%s</%s>" % (tag, style_attr, content, tag)
    return content


_THEME_ALIASES = {
    "text1": "dk1",
    "text2": "dk2",
    "bg1": "lt1",
    "bg2": "lt2",
    "dark1": "dk1",
    "dark2": "dk2",
    "light1": "lt1",
    "light2": "lt2",
}


def _resolve_shd(shd, theme_colors=None):
    """Resolve a w:shd element to a CSS hex color."""
    if shd is None:
        return None
    theme_colors = theme_colors or {}
    fill = shd.get(_qn("fill"))
    color = _color(fill)
    if not color:
        theme = (shd.get(_qn("themeFill")) or "").lower()
        theme = _THEME_ALIASES.get(theme, theme)
        if theme in theme_colors:
            color = theme_colors[theme]
        elif theme in ("accent1", "dk1", "dk2"):
            color = "#%s" % HEADER_FILL
        elif theme in ("lt1", "lt2"):
            color = "#FFFFFF"
    if not color:
        return None
    shade = shd.get(_qn("themeFillShade"))
    tint = shd.get(_qn("themeFillTint"))
    return _apply_shade_tint(color, shade=shade, tint=tint)


def _apply_shade_tint(hex_color, shade=None, tint=None):
    """Apply OOXML themeFillShade / themeFillTint (hex 00-FF) to a color."""
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return hex_color
    try:
        r, g, b = (int(color[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return hex_color
    factor = None
    toward = None
    if shade:
        try:
            # shade: blend toward black; higher = darker
            amount = int(shade, 16) / 255.0
            factor = amount
            toward = (0, 0, 0)
        except ValueError:
            pass
    elif tint:
        try:
            amount = int(tint, 16) / 255.0
            factor = amount
            toward = (255, 255, 255)
        except ValueError:
            pass
    if factor is None or toward is None:
        return "#%s" % color.upper()
    # OOXML: result = color * factor/255 style; approximate blend
    r = int(r * factor + toward[0] * (1 - factor))
    g = int(g * factor + toward[1] * (1 - factor))
    b = int(b * factor + toward[2] * (1 - factor))
    return "#%02X%02X%02X" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _cell_shading(tc, theme_colors=None):
    shd = _find(tc, "./w:tcPr/w:shd")
    color = _resolve_shd(shd, theme_colors)
    if color:
        return color
    # Google Docs sometimes puts the fill on the first paragraph instead
    for p in _findall(tc, "./w:p")[:1]:
        p_shd = _find(p, "./w:pPr/w:shd")
        color = _resolve_shd(p_shd, theme_colors)
        if color:
            return color
    return None


def _cell_borders(tc, tbl_borders):
    borders = dict(tbl_borders or {})
    tc_borders = _find(tc, "./w:tcPr/w:tcBorders")
    if tc_borders is not None:
        for side in ("top", "left", "bottom", "right"):
            el = _find(tc_borders, "./w:%s" % side)
            if el is None:
                continue
            val = (el.get(_qn("val")) or "").lower()
            if val in ("nil", "none", "false"):
                borders[side] = "none"
                continue
            color = _color(el.get(_qn("color"))) or "#000000"
            sz = el.get(_qn("sz"))
            width = max(1, int(sz) // 4) if sz and sz.isdigit() else 1
            borders[side] = "%spx solid %s" % (width, color)
    return borders


def _tbl_borders(tbl):
    borders = {}
    tbl_borders = _find(tbl, "./w:tblPr/w:tblBorders")
    if tbl_borders is None:
        # Google Docs / Word forms almost always intend a grid
        return {
            "top": "1px solid #000000",
            "left": "1px solid #000000",
            "bottom": "1px solid #000000",
            "right": "1px solid #000000",
            "insideH": "1px solid #000000",
            "insideV": "1px solid #000000",
        }
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = _find(tbl_borders, "./w:%s" % side)
        if el is None:
            continue
        val = (el.get(_qn("val")) or "").lower()
        if val in ("nil", "none", "false"):
            borders[side] = "none"
            continue
        color = _color(el.get(_qn("color"))) or "#000000"
        sz = el.get(_qn("sz"))
        width = max(1, int(sz) // 4) if sz and sz.isdigit() else 1
        borders[side] = "%spx solid %s" % (width, color)
    if not borders:
        borders = {
            "top": "1px solid #000000",
            "left": "1px solid #000000",
            "bottom": "1px solid #000000",
            "right": "1px solid #000000",
        }
    return borders


def _colspan(tc):
    span = _find(tc, "./w:tcPr/w:gridSpan")
    if span is None:
        return 1
    val = span.get(_qn("val"))
    return int(val) if val and val.isdigit() else 1


def _cell_width_style(tc):
    width = _find(tc, "./w:tcPr/w:tcW")
    if width is None:
        return None
    w_val = width.get(_qn("w"))
    w_type = (width.get(_qn("type")) or "").lower()
    if not w_val or not w_val.isdigit():
        return None
    num = int(w_val)
    if w_type == "pct":
        # OOXML pct is 1/50 of a percent
        return "width:%.2f%%" % (num / 50.0)
    if w_type == "dxa":
        # twips → mm roughly for editor hint
        return "width:%.1fpt" % (num / 20.0)
    return None


def _is_header_fill(fill):
    if not fill:
        return False
    hexval = fill.lstrip("#").upper()
    return hexval in HEADER_FILL_ALT or hexval == HEADER_FILL


def _cell_to_html(tc, media, tbl_borders, force_header=False, theme_colors=None):
    paragraphs = []
    for p in _findall(tc, "./w:p"):
        paragraphs.append(_paragraph_to_html(p, media))
    # Nested tables
    for nested in _findall(tc, "./w:tbl"):
        paragraphs.append(_table_to_html(nested, media, theme_colors))
    content = "".join(paragraphs).strip() or "<p><br/></p>"
    # Editor needs a block + BR inside empty cells to place the caret
    if content in ("&nbsp;", "\xa0", "<br/>", "<br>"):
        content = "<p><br/></p>"
    fill = _cell_shading(tc, theme_colors)
    borders = _cell_borders(tc, tbl_borders)
    styles = [
        "border-collapse:collapse",
        "vertical-align:top",
        "padding:4px 6px",
    ]
    for side, css_side in (
        ("top", "border-top"),
        ("left", "border-left"),
        ("bottom", "border-bottom"),
        ("right", "border-right"),
    ):
        styles.append("%s:%s" % (css_side, borders.get(side, "1px solid #000000")))
    text = _text_of(tc).strip()
    looks_like_casilla = bool(re.match(r"^CASILLA\b", text, re.I))
    if force_header or _is_header_fill(fill) or looks_like_casilla:
        # Keep source fill when present; fall back to navy for CASILLA bands
        bg = fill if fill and fill.upper() not in ("#FFFFFF", "#FFF") else "#%s" % HEADER_FILL
        styles.append("background-color:%s" % bg)
        if _is_dark_color(bg):
            styles.append("color:#FFFFFF")
        styles.append("font-weight:bold")
    elif fill:
        styles.append("background-color:%s" % fill)
        if _is_dark_color(fill):
            styles.append("color:#FFFFFF")
    width_style = _cell_width_style(tc)
    if width_style:
        styles.append(width_style)
    colspan = _colspan(tc)
    colspan_attr = ' colspan="%s"' % colspan if colspan > 1 else ""
    tag = "th" if (force_header or looks_like_casilla) else "td"
    return "<%s%s style=\"%s\">%s</%s>" % (
        tag,
        colspan_attr,
        ";".join(styles),
        content,
        tag,
    )


def _is_dark_color(hex_color):
    color = (hex_color or "").lstrip("#")
    if len(color) != 6:
        return False
    try:
        r, g, b = (int(color[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    # Perceived luminance
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def _table_to_html(tbl, media, theme_colors=None):
    tbl_borders = _tbl_borders(tbl)
    rows_html = []
    rows = _findall(tbl, "./w:tr")
    for index, tr in enumerate(rows):
        cells = _findall(tr, "./w:tc")
        force_header = False
        if cells:
            row_text = " ".join(_text_of(tc).strip() for tc in cells).strip()
            if re.match(r"^CASILLA\b", row_text, re.I):
                force_header = True
            elif index == 0 and len(cells) == 1:
                # Single full-width first row often is the section header
                shd = _cell_shading(cells[0], theme_colors)
                if _is_header_fill(shd) or row_text.isupper():
                    force_header = True
        tds = "".join(
            _cell_to_html(
                tc,
                media,
                tbl_borders,
                force_header=force_header,
                theme_colors=theme_colors,
            )
            for tc in cells
        )
        rows_html.append("<tr>%s</tr>" % tds)
    table_style = (
        "border-collapse:collapse;width:100%;margin:8px 0;"
        "border:1px solid #000000;table-layout:fixed;"
    )
    return (
        '<table class="o_document_form_table" style="%s">%s</table>'
        % (table_style, "".join(rows_html))
    )


def _enhance_html(html):
    """Normalize mammoth/partial HTML so form tables still look like the source."""
    if not html:
        return ""
    already_styled = "o_document_form_table" in html
    if "<table" in html and not already_styled:

        def _table_open(match):
            attrs = match.group(1) or ""
            style = (
                "border-collapse:collapse;width:100%;margin:8px 0;"
                "border:1px solid #000;table-layout:fixed;"
            )
            if "style=" in attrs:
                attrs = re.sub(
                    r'style="([^"]*)"',
                    lambda m: 'style="%s;%s"' % (m.group(1).rstrip(";"), style),
                    attrs,
                    count=1,
                )
                return '<table class="o_document_form_table"%s>' % attrs
            return (
                '<table class="o_document_form_table" style="%s"%s>'
                % (style, attrs)
            )

        html = re.sub(r"<table(\s[^>]*)?>", _table_open, html, flags=re.I)
        html = re.sub(
            r"<td(\s[^>]*)?>",
            lambda m: _ensure_td_style(m.group(0)),
            html,
            flags=re.I,
        )
        html = re.sub(
            r"<th(\s[^>]*)?>",
            lambda m: _ensure_td_style(m.group(0), header=True),
            html,
            flags=re.I,
        )
    if not already_styled:
        html = re.sub(
            r"(<t[dh]\b[^>]*>)(\s*(?:<p[^>]*>)?\s*(?:<strong>)?\s*CASILLA\b)",
            _inject_header_style,
            html,
            flags=re.I | re.S,
        )
    return _ensure_editable_cells(html)


def _ensure_editable_cells(html):
    """Empty table cells need a block+BR so the caret can land on click."""

    def _repl(match):
        open_tag, inner, close_tag = match.group(1), match.group(2), match.group(3)
        compact = re.sub(r"\s+", "", inner or "")
        compact = (
            compact.replace("&nbsp;", "")
            .replace("&#160;", "")
            .replace("\xa0", "")
            .lower()
        )
        empty_markers = (
            "",
            "<br>",
            "<br/>",
            "<br />",
            "<p></p>",
            "<p><br></p>",
            "<p><br/></p>",
            "<p><br /></p>",
            "<div></div>",
            "<div><br></div>",
            "<div><br/></div>",
        )
        if compact in empty_markers:
            return "%s<p><br/></p>%s" % (open_tag, close_tag)
        if "<" not in (inner or "") and not (inner or "").strip():
            return "%s<p><br/></p>%s" % (open_tag, close_tag)
        return match.group(0)

    return re.sub(
        r"(<(?:td|th)\b[^>]*>)(.*?)(</(?:td|th)>)",
        _repl,
        html,
        flags=re.I | re.S,
    )


def _ensure_td_style(tag_open, header=False):
    base = (
        "border:1px solid #000;padding:4px 6px;vertical-align:top;"
    )
    if header:
        base += "background-color:#%s;color:#fff;font-weight:bold;" % HEADER_FILL
    if "style=" in tag_open:
        return re.sub(
            r'style="([^"]*)"',
            lambda m: 'style="%s;%s"' % (m.group(1).rstrip(";"), base),
            tag_open,
            count=1,
        )
    if tag_open.endswith("/>"):
        return tag_open[:-2] + ' style="%s"/>' % base
    return tag_open[:-1] + ' style="%s">' % base


def _inject_header_style(match):
    tag = match.group(1)
    rest = match.group(2)
    style = (
        "background-color:#%s;color:#FFFFFF;font-weight:bold;"
        "border:1px solid #000;padding:4px 6px;vertical-align:top;"
        % HEADER_FILL
    )
    if "style=" in tag:
        tag = re.sub(
            r'style="([^"]*)"',
            lambda m: 'style="%s;%s"' % (m.group(1).rstrip(";"), style),
            tag,
            count=1,
        )
    else:
        tag = tag[:-1] + ' style="%s">' % style
    return tag + rest
