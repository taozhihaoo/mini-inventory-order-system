"""CSV helpers: cell sanitization against formula injection on export."""

from __future__ import annotations

_RISKY_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_value(value: str) -> str:
    """Neutralize spreadsheet formula injection (=, +, -, @, tab, CR prefixes)."""
    if value.startswith(_RISKY_PREFIXES):
        return "'" + value
    return value
