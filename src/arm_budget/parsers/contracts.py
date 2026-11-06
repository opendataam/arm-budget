"""Parser of the contract pages (Popup.php?page=SITE_C) of an expenditure line.

Layout: a header row (Գործընկեր | Պայմ.սկիզբ | Պայմ.ավարտ | Պայմ.գումարը | Վճարված գումար)
followed, for every contract, by a data row (td0L/td0R cells) and a row with the
links to the contract files (procurement system armeps.am and scanned payment documents).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .common import clean_label, parse_date, parse_number

_HEADER = re.compile(r'<td class="td00">([^<]*)</td>')
_ROW = re.compile(r"<tr>((?:<td class=\"td0[LR]\">[^<]*</td>)+)</tr>")
_CELL = re.compile(r'<td class="td0[LR]">([^<]*)</td>')
_FILES = re.compile(r'<div class="collapse\s*" id="DIV(\d+)">(.*?)</td>', re.DOTALL)
_LINK = re.compile(r'<a target="_blank" href="([^"]+)">([^<]*)</a>')

EXPECTED_HEADER = ["Գործընկեր", "Պայմ.սկիզբ", "Պայմ.ավարտ", "Պայմ.գումարը", "Վճարված գումար"]


@dataclass
class Contract:
    seq: int
    partner: str | None
    start_raw: str
    end_raw: str
    amount_raw: str
    paid_raw: str
    files: list[tuple[str, str]] = field(default_factory=list)  # (url, link text)

    @property
    def start_date(self):
        return parse_date(self.start_raw)

    @property
    def end_date(self):
        return parse_date(self.end_raw)

    @property
    def amount(self):
        return parse_number(self.amount_raw)

    @property
    def paid(self):
        return parse_number(self.paid_raw)


def file_url(href: str, base: str) -> str:
    href = href.replace("\\", "/")
    if re.match(r"https?://", href):
        return href
    return f"{base.rstrip('/')}/{href.lstrip('/')}"


def parse_contracts(text: str, base_url: str) -> tuple[list[str], list[Contract]]:
    header = [clean_label(h) or "" for h in _HEADER.findall(text)]
    rows = [[c for c in _CELL.findall(m.group(1))] for m in _ROW.finditer(text)]
    files = {int(n): [(file_url(u, base_url), t) for u, t in _LINK.findall(body)] for n, body in _FILES.findall(text)}
    out = []
    for i, cells in enumerate(rows, start=1):
        cells = (cells + [""] * 5)[:5]
        out.append(Contract(i, clean_label(cells[0]), cells[1].strip(), cells[2].strip(), cells[3].strip(), cells[4].strip(),
                            files.get(i, [])))
    return header, out
