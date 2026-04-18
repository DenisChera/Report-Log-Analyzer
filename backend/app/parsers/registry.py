from app.parsers.base import BaseParser
from app.parsers.html_parser import MtsHtmlParser

# Register all available parsers here. Order matters — first match wins.
_PARSERS: list[BaseParser] = [
    MtsHtmlParser(),
]


class UnsupportedFormatError(Exception):
    pass


def get_parser(filename: str, content: bytes) -> BaseParser:
    """Auto-detect file format and return the appropriate parser."""
    for parser in _PARSERS:
        if parser.can_parse(filename, content):
            return parser
    raise UnsupportedFormatError(
        f"No parser available for '{filename}'. "
        f"Supported formats: {', '.join(p.__class__.__name__ for p in _PARSERS)}"
    )
