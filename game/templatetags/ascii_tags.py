from django import template

from .. import ascii_art
from ..novel_prose import strip_stat_tail

register = template.Library()


@register.filter
def prose(text):
    """Хроніка читається як роман: без числових хвостів і службових позначок."""
    out = strip_stat_tail(str(text or ""))
    return out.lstrip("★✦◆ ").strip()


@register.filter
def prose_title(text):
    """«Пророцтво Комети: Випустити спалах» → «…: випустити спалах»."""
    out = strip_stat_tail(str(text or "")).lstrip("★✦◆ ").strip()
    head, sep, tail = out.partition(": ")
    if sep and tail and tail[0].isupper() and not tail.split(" ", 1)[0].isupper():
        tail = tail[0].lower() + tail[1:]
    return head + sep + tail


@register.filter
def item_ascii(item):
    """Return catalog ASCII art for an Item (or InventoryItem) instance."""
    if item is None:
        return ascii_art.get_item_art()
    name = getattr(item, 'name', '') or ''
    item_type = getattr(item, 'item_type', None)
    return ascii_art.get_item_art(name, item_type)


@register.filter
def item_ascii_key(item):
    """Return the resolved ITEM_ART key for an Item instance."""
    if item is None:
        return ascii_art.FALLBACK_ITEM_KEY
    return ascii_art.get_item_art_key(
        getattr(item, 'name', '') or '',
        getattr(item, 'item_type', None),
    )


@register.filter
def item_ascii_font(item, width=150):
    """Font size (px) that fits this item's ASCII art inside a thumbnail box."""
    rows, cols = ascii_art.item_art_dimensions(item_ascii(item))
    try:
        width = float(width)
    except (TypeError, ValueError):
        width = 150.0
    height = width * 0.5
    by_width = width / max(cols * 0.62, 1.0)
    by_height = height / max(rows, 1)
    return round(max(2.6, min(by_width, by_height, 9.0)), 2)


@register.filter
def ascii_by_key(arts, key):
    """Look up an art block in a catalog dict (default empty string)."""
    if not isinstance(arts, dict):
        return ''
    return arts.get(key, '')
