"""Parser of the w2ui grids embedded in the report pages.

Every report result is an HTML page with a JavaScript call
``$('#grid').w2grid({ header: ..., columns: [...], records: [...] })``.
Records are JavaScript object literals, one per line::

    { recid: 2,c2: 'ՊԱՇՏՊԱՆՈՒԹՅՈՒՆ',c8: '145164212.9',c9: '57525982.3965',c10: '40%', ... },
    { recid: 3,c2: '...', ..., w2ui: { "style": "background-color: #3CF" }},

Values are single-quoted strings. The field set differs between rows: in a
grouped (tree) result each row carries only the label of its own level.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_HEADER = re.compile(r"\bheader:\s*'((?:[^'\\]|\\.)*)'")
_COLUMNS = re.compile(r"\bcolumns:\s*\[(.*?)\]\s*,?\s*(?:toolbar|records)\b", re.DOTALL)
_COLUMN = re.compile(r"\{\s*field:\s*'(c\d+)',\s*caption:\s*'((?:[^'\\]|\\.)*)'([^}]*)\}")
_SEARCHES = re.compile(r"\bsearches:\s*\[(.*?)\]", re.DOTALL)
_RECORDS = re.compile(r"\brecords:\s*\[(.*?)\]\s*\}\);", re.DOTALL)
_RECORD_START = re.compile(r"\{\s*recid:\s*(\d+)\s*,")
_FIELD = re.compile(r"(c\d+):\s*'((?:[^'\\]|\\.)*)'")
_W2UI = re.compile(r"w2ui:\s*(\{.*?\})\s*\}\s*,?\s*$", re.DOTALL)
_JS_ESCAPE = re.compile(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", re.DOTALL)


def js_unescape(s: str) -> str:
    def repl(m: re.Match) -> str:
        e = m.group(1)
        if e[0] in "ux" and len(e) > 1:
            return chr(int(e[1:], 16))
        return {"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(e, e)

    return _JS_ESCAPE.sub(repl, s)


@dataclass
class Column:
    field: str
    caption: str
    numeric: bool


@dataclass
class Record:
    recid: int
    values: dict[str, str]
    style: str | None = None


@dataclass
class Grid:
    header: str | None
    columns: list[Column]
    group_columns: list[Column] = field(default_factory=list)  # the "searches" list = the grouping columns
    records: list[Record] = field(default_factory=list)

    def caption(self, fld: str) -> str | None:
        for c in self.columns:
            if c.field == fld:
                return c.caption
        return None


def parse_grid(html: str) -> Grid | None:
    """Return the grid of a page, or None if the page has no w2grid."""
    i = html.find(".w2grid(")
    if i < 0:
        return None
    js = html[i:]
    hm = _HEADER.search(js)
    cm = _COLUMNS.search(js)
    columns = []
    if cm:
        for f, cap, rest in _COLUMN.findall(cm.group(1)):
            columns.append(Column(f, js_unescape(cap), "align=right" in rest or "render:" in rest))
    group_columns = []
    sm = _SEARCHES.search(js[: cm.start()] if cm else js)
    if sm:
        for f, cap, _ in _COLUMN.findall(sm.group(1)):
            group_columns.append(Column(f, js_unescape(cap), False))
    records: list[Record] = []
    rm = _RECORDS.search(js)
    if rm:
        body = rm.group(1)
        starts = [m for m in _RECORD_START.finditer(body)]
        for k, m in enumerate(starts):
            chunk = body[m.end(): starts[k + 1].start() if k + 1 < len(starts) else len(body)]
            style = None
            wm = _W2UI.search(chunk)
            if wm:
                try:
                    style = json.loads(wm.group(1)).get("style")
                except ValueError:
                    style = wm.group(1)
                chunk = chunk[: wm.start()]
            values = {f: js_unescape(v) for f, v in _FIELD.findall(chunk)}
            records.append(Record(int(m.group(1)), values, style))
    return Grid(js_unescape(hm.group(1)) if hm else None, columns, group_columns, records)
