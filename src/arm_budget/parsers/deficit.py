"""Structure of the deficit financing report.

The report is a formatted statement (not a classifier tree)::

    ԸՆԴԱՄԵՆԸ                                       total
    այդ թվում`                                     note ("including"), no values
    Ա. Ներքին աղբյուրներ-ընդամենը                  source A (domestic)
    1. Փոխառու միջոցներ                            item A.1
    1.1 Արժեթղթերի թողարկումից ...                 subitem A.1.1
    ՀՀ Ֆինանսների նախարարություն                   detail of A.1.1
    որից`                                          note ("of which")
       Գանձապետական պարտատոմսեր                    detail (indented)
    ...
    Բ. Արտաքին աղբյուրներ-ընդամենը                 source B (external)

Only the numbered lines form an additive hierarchy; detail lines are breakdowns
(bodies, companies, loans) that may overlap and need not add up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .common import is_total_label

SOURCE_LETTERS = {"Ա": "A", "Բ": "B", "Գ": "C", "Դ": "D"}
NOTES = ("այդ թվում", "որից")

_SOURCE = re.compile(r"^([ԱԲԳԴ])\.\s*")
_SUBITEM = re.compile(r"^(\d+)\.(\d+)\.?\s+")
_ITEM = re.compile(r"^(\d+)\.\s+")


@dataclass
class DeficitLine:
    line_no: int
    label: str
    kind: str
    level: int
    item_code: str | None
    parent: int | None
    note: str | None
    indent: int


def classify(labels: list[str]) -> list[DeficitLine]:
    out: list[DeficitLine] = []
    source = None
    last_by_level: dict[int, int] = {}
    note = None
    for i, raw in enumerate(labels, start=1):
        indent = len(raw) - len(raw.lstrip(" "))
        label = raw.strip()
        plain = label.rstrip("`՝' :").strip()
        if is_total_label(label) and not out:
            out.append(DeficitLine(i, label, "total", 0, "TOTAL", None, None, indent))
            last_by_level = {0: i}
            continue
        if plain in NOTES:
            out.append(DeficitLine(i, label, "note", None, None, out[-1].line_no if out else None, None, indent))
            note = plain
            continue
        m = _SOURCE.match(label)
        if m:
            source = SOURCE_LETTERS.get(m.group(1), m.group(1))
            line = DeficitLine(i, label, "source", 1, source, last_by_level.get(0), None, indent)
        elif (m := _SUBITEM.match(label)) and source:
            line = DeficitLine(i, label, "subitem", 3, f"{source}.{int(m.group(1))}.{int(m.group(2))}",
                               last_by_level.get(2), None, indent)
        elif (m := _ITEM.match(label)) and source:
            line = DeficitLine(i, label, "item", 2, f"{source}.{int(m.group(1))}", last_by_level.get(1), None, indent)
        else:
            parent = last_by_level.get(3) or last_by_level.get(2) or last_by_level.get(1) or last_by_level.get(0)
            line = DeficitLine(i, label, "detail", 4, None, parent, note, indent)
            out.append(line)
            continue
        note = None
        last_by_level[line.level] = i
        for lvl in [k for k in last_by_level if k > line.level]:
            del last_by_level[lvl]
        out.append(line)
    return out
