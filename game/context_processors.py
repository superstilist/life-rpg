"""Template context processor: makes the ASCII art catalog available everywhere."""
from . import ascii_art


def ascii_art_context(request):
    """Inject ASCII art collections into every template context."""
    return {
        'ASCII_BG_ART': ascii_art.get_bg_art(),
        'ASCII_BG_ARTS': ascii_art.BG_ART,
        'ASCII_UI_ARTS': ascii_art.UI_ART,
        'ASCII_MENU_ARTS': ascii_art.MENU_ART,
        'ASCII_ITEM_ARTS': ascii_art.ITEM_ART,
    }
