from abc import ABC, abstractmethod

from app.models import ParsedReport


class BaseParser(ABC):
    """Abstract base for all report parsers.
    Every new format (HTML, XML, JSON, CSV, ...) must implement this interface.
    The rest of the pipeline only depends on ParsedReport — never on the parser."""

    @abstractmethod
    def can_parse(self, filename: str, content: bytes) -> bool:
        """Return True if this parser can handle the given file.
        Used by the registry for auto-detection."""
        ...

    @abstractmethod
    def parse(self, filename: str, content: bytes) -> ParsedReport:
        """Parse raw file bytes into a format-agnostic ParsedReport."""
        ...
