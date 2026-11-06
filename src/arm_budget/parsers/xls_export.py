"""Parser of the Excel exports (xml/xmlopen.php -> xml/temp/<session>.xls).

The export is an XML Spreadsheet 2003 (SpreadsheetML) workbook with one sheet:
row 2 is a title with the date the data refer to ('ԲՅՈՒՋԵ ԾԱԽՍԵՐ  առ 04/11/26  -  հազ. դրամներով'),
row 3 the column captions, then the rows of the grid with values rounded to 2 decimals.
The collector uses the export only for the "as of" date; values are taken from the
grid, which has 4 decimals.
"""

from __future__ import annotations

import datetime as dt
import html
import re

from .common import clean_label, parse_date

_ROW = re.compile(r"<Row\b.*?</Row>", re.DOTALL)
_CELL = re.compile(r"<Cell\b.*?</Cell>|<Cell\b[^>]*/>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_AS_OF = re.compile(r"\bառ\s+(\d{1,2}/\d{1,2}/\d{2,4})")


def parse_rows(text: str) -> list[list[str]]:
    i = text.find("<Worksheet")
    out = []
    for row in _ROW.findall(text[i:] if i >= 0 else text):
        out.append([html.unescape(_TAG.sub("", c)) for c in _CELL.findall(row)])
    return out


def parse_title(text: str) -> tuple[str | None, dt.date | None]:
    """(title, as-of date) of an export."""
    for row in parse_rows(text)[:5]:
        for cell in row:
            m = _AS_OF.search(cell)
            if m:
                return clean_label(cell), parse_date(m.group(1))
    return None, None
