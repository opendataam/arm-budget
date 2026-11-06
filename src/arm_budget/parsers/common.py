"""Cleaning of values and labels."""

from __future__ import annotations

import datetime as dt
import html
import re
import unicodedata
from decimal import Decimal, InvalidOperation

_NUM_CLEAN = re.compile(r"[,\s ]")


def parse_number(s: str | None) -> float | None:
    """'1,234.50' -> 1234.5; '(1,234.50)' -> -1234.5; '' -> None."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = _NUM_CLEAN.sub("", s.strip("()"))
    if s.startswith("-"):
        neg, s = not neg, s[1:]
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def parse_decimal(s: str | None) -> Decimal | None:
    """Exact value of an amount cell: '1,234.5678' -> Decimal('1234.5678'); '(12.30)' -> Decimal('-12.30')."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = _NUM_CLEAN.sub("", s.strip("()"))
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    return -v if neg else v


def parse_percent(s: str | None) -> float | None:
    """'84%' -> 84.0; '(27)%' -> -27.0; '' -> None."""
    if s is None:
        return None
    return parse_number(s.replace("%", ""))


def parse_date(s: str | None) -> dt.date | None:
    """'15/01/26' or '15/01/2026' -> date(2026, 1, 15)."""
    if not s:
        return None
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\s*", s)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def clean_label(s: str | None) -> str | None:
    """Label as displayed: HTML entities decoded, line breaks of the source database removed,
    whitespace collapsed. The source DB stores long names wrapped in fixed-width chunks
    (e.g. 'պտուղն\\nերից'), so a line break is removed without inserting a space."""
    if s is None:
        return None
    s = html.unescape(s).replace("\r", "").replace("\n", "").replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s).strip()
    return s or None


_KEEP = re.compile(r"[^0-9a-zա-և]+")
# Latin letters that the source sometimes uses instead of look-alike Armenian ones
_LOOKALIKE = str.maketrans({"u": "ս", "o": "օ", "h": "հ", "n": "ո"})


def norm_key(s: str | None) -> str:
    """Matching key of a label: lower case, letters and digits only.

    The grid drops commas and other punctuation from the names that the filter lists
    keep (and adds a '- ' prefix to economic articles), so names are compared by letters only.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", html.unescape(s)).lower().replace("և", "եւ").translate(_LOOKALIKE)
    return _KEEP.sub("", s)


def is_total_label(s: str | None) -> bool:
    """'  Ը  Ն  Դ  Ա  Մ  Ե  Ն  Ը  ' (letter-spaced) or 'ԸՆԴԱՄԵՆԸ'."""
    return bool(s) and norm_key(s).startswith("ընդամենը")
