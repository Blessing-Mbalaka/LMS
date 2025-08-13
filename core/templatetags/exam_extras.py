# core/templatetags/exam_extras.py
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.conf import settings

register = template.Library()

def _normalize_rows(rows):
    """
    Return rows as a list[list[str]] no matter the input shape.
    Accepts:
      - [{'cells': [{'text': 'A'}, {'text': 'B'}]}, ...]
      - [['A','B'], ['C','D']]
    """
    normalized = []

    if not rows:
        return normalized

    # Case A: list of dict rows with 'cells'
    if isinstance(rows[0], dict):
        for r in rows:
            cells = r.get("cells", [])
            normalized.append([
                str(c.get("text", "")) if isinstance(c, dict) else str(c)
                for c in cells
            ])
        return normalized

    # Case B: list of lists
    if isinstance(rows[0], (list, tuple)):
        for r in rows:
            normalized.append([str(c) for c in r])
        return normalized

    # Fallback: treat as a single row
    return [[str(x) for x in rows]]

def _render_table(item):
    """Render a table content item to HTML safely."""
    # If HTML was prebuilt, just use it
    html = item.get("html")
    if isinstance(html, str) and html.strip():
        return html

    rows = item.get("rows") or []
    rows = _normalize_rows(rows)

    if not rows:
        return "<div class='text-muted'><em>[Empty table]</em></div>"

    # Detect header: if first row looks like header, wrap with <th>
    # Simple heuristic: if more than 1 row, assume row 0 is header
    header = rows[0] if len(rows) > 1 else None
    body = rows[1:] if header else rows

    out = ["<div class='table-responsive'><table class='table table-bordered table-sm mb-2'>"]

    if header:
        out.append("<thead><tr>")
        for cell in header:
            out.append(f"<th>{escape(cell)}</th>")
        out.append("</tr></thead>")

    out.append("<tbody>")
    for r in body:
        out.append("<tr>")
        for cell in r:
            out.append(f"<td>{escape(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")

    return "".join(out)


def _is_abs_url(s: str) -> bool:
    s = str(s).lower()
    return s.startswith("http://") or s.startswith("https://") or s.startswith("data:")

def _join_media(url_part: str, default_folder: str = "") -> str:
    """
    Convert 'foo.png' -> '/media/foo.png' (or '/media/<default_folder>/foo.png').
    Keeps absolute URLs and '/...' paths unchanged.
    """
    if _is_abs_url(url_part):
        return url_part
    if url_part.startswith("/"):
        return url_part
    base = getattr(settings, "MEDIA_URL", "/media/")
    if not base.endswith("/"):
        base += "/"
    default_folder = (default_folder or "").strip("/")
    return f"{base}{default_folder + '/' if default_folder else ''}{url_part}".replace("//", "/")

def _render_figure(item):
    """
    Supports:
      - {'type':'figure','data_uri':'data:image/png;base64,...'}
      - {'type':'figure','url':'/media/.../img.png'}
      - {'type':'figure','images':['filename.png', 'nested/f1.jpg']}
      - {'type':'figure','images':[{'path':'x.png'}, {'url':'https://...'}, {'data_uri':'data:...'}]}
      - {'type':'image', ...} as alias
    """
    # inline data uri on the item itself
    data_uri = item.get("data_uri")
    if isinstance(data_uri, str) and data_uri.startswith("data:"):
        return f"<div class='my-2'><img src='{data_uri}' class='img-fluid' /></div>"

    # direct url on the item
    if isinstance(item.get("url"), str):
        return f"<div class='my-2'><img src='{escape(item['url'])}' class='img-fluid' /></div>"

    # images can be many shapes
    images = item.get("images") or item.get("image") or []
    if isinstance(images, (str, bytes)):
        images = [images]
    elif not isinstance(images, (list, tuple)):
        images = [images]

    DEFAULT_FIG_FOLDER = ""  # e.g. "extracted/figures" if you store under MEDIA_ROOT/extracted/figures

    tags = []
    for im in images:
        # dict form with possible keys
        if isinstance(im, dict):
            if isinstance(im.get("data_uri"), str) and im["data_uri"].startswith("data:"):
                tags.append(f"<img src='{im['data_uri']}' class='img-fluid me-2 mb-2' />")
                continue
            if isinstance(im.get("url"), str):
                tags.append(f"<img src='{escape(im['url'])}' class='img-fluid me-2 mb-2' />")
                continue
            path_like = im.get("path") or im.get("filename") or im.get("name")
            if path_like:
                url = _join_media(str(path_like), DEFAULT_FIG_FOLDER)
                tags.append(f"<img src='{escape(url)}' class='img-fluid me-2 mb-2' />")
                continue
        else:
            # string/bytes
            src = im.decode() if isinstance(im, bytes) else str(im)
            url = src if _is_abs_url(src) or src.startswith("/") else _join_media(src, DEFAULT_FIG_FOLDER)
            tags.append(f"<img src='{escape(url)}' class='img-fluid me-2 mb-2' />")

    if tags:
        return "<div class='my-2'>" + "".join(tags) + "</div>"
    return "<div class='text-muted'><em>[Figure/Image available]</em></div>"

@register.filter
def render_block(item):
    """
    Render a structured content item (dict) to HTML.
    Expected keys:
      - type: 'question_text' | 'table' | 'case_study' | 'figure' | 'image'
      - text / rows / html / data_uri / images
    """
    if not isinstance(item, dict):
        return mark_safe(f"<p>{escape(str(item))}</p>")

    t = (item.get("type") or "").lower()

    if t in ("question_text", "text", "paragraph", "instruction"):
        txt = item.get("text", "")
        return mark_safe(f"<p>{escape(txt)}</p>") if txt else ""

    if t == "case_study":
        txt = item.get("text", "")
        return mark_safe(f"<div class='case-study'>{escape(txt)}</div>")

    if t == "table":
        return mark_safe(_render_table(item))

    if t in ("figure", "image"):
        return mark_safe(_render_figure(item))

    # Fallback for unknown types
    return mark_safe(f"<p>{escape(str(item))}</p>")