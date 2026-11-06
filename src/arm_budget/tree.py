"""Turn a grouped report grid into a tree of nodes.

A query grouped by N classifiers returns a tree in depth-first order: the first
row is the grand total, then each row carries the label of exactly one level
(the column of that level), followed by its children, e.g. for expenditures::

    c2 section  ->  c3 group  ->  c4 class  ->  c5 program  ->  c6 department  ->  c7 article

Siblings are ordered by code. Rows of the deepest level are the leaves (the
finest data the site publishes); the other rows are subtotals.

A query grouped by "contracts" returns a flat list instead: every row carries the
labels of all levels and the line id (c20).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .parsers.common import is_total_label, norm_key, parse_number, parse_percent
from .parsers.grid import Grid

VALUE_KEYS = [f"{p}_{m}" for p, m in config.VALUE_COLUMNS]  # q1_plan, q1_actual, q1_pct, h1_plan, ...
AMOUNT_KEYS = [k for k in VALUE_KEYS if not k.endswith("_pct")]
LINE_ID_CAPTION = "Պայմանագիր"


@dataclass
class Node:
    recid: int
    level: int                     # 0 .. n_levels-1; -1 for the grand total
    label: str
    raw: dict[str, str]            # the 12 value cells as in the source
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)
    code: str | None = None        # resolved classifier code
    method: str | None = None      # how the code was resolved: name | probe
    candidates: set[str] = field(default_factory=set)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def path(self) -> list[Node]:
        out, n = [], self
        while n is not None and n.level >= 0:
            out.append(n)
            n = n.parent
        return out[::-1]

    def key(self) -> tuple:
        """Labels of the node and its ancestors, normalised."""
        return tuple(norm_key(n.label) for n in self.path())

    def amounts(self) -> tuple:
        return tuple(round(v, 4) if v is not None else None for v in (parse_number(self.raw.get(k)) for k in AMOUNT_KEYS))

    def signature(self) -> tuple:
        return self.key() + self.amounts()

    def value(self, key: str) -> float | None:
        s = self.raw.get(key)
        return parse_percent(s) if key.endswith("_pct") else parse_number(s)


def value_fields(grid: Grid) -> list[str]:
    """Fields of the 12 value columns (plan, actual, % for Q1, H1, 9 months, year)."""
    group = {c.field for c in grid.group_columns}
    fields = [c.field for c in grid.columns if c.field not in group and c.caption != LINE_ID_CAPTION]
    if not grid.group_columns:  # deficit: the first column is the label
        fields = fields[1:]
    if len(fields) != len(VALUE_KEYS):
        raise ValueError(f"expected {len(VALUE_KEYS)} value columns, got {len(fields)}: {[c.caption for c in grid.columns]}")
    return fields


def line_id_field(grid: Grid) -> str | None:
    for c in grid.columns:
        if c.caption == LINE_ID_CAPTION:
            return c.field
    return None


def _raw(grid_fields: list[str], values: dict[str, str]) -> dict[str, str]:
    return {k: values.get(f, "") for k, f in zip(VALUE_KEYS, grid_fields)}


def build_tree(grid: Grid) -> tuple[Node, list[Node]]:
    """(grand total, nodes in source order) of a grouped (tree) result."""
    gfields = [c.field for c in grid.group_columns]
    vfields = value_fields(grid)
    total = None
    nodes: list[Node] = []
    stack: list[Node | None] = [None] * len(gfields)
    for i, rec in enumerate(grid.records):
        present = [lvl for lvl, f in enumerate(gfields) if f in rec.values]
        if not present:
            raise ValueError(f"record {rec.recid} has no label")
        lvl = present[0]
        label = rec.values[gfields[lvl]]
        if i == 0 and is_total_label(label):
            total = Node(rec.recid, -1, label, _raw(vfields, rec.values))
            continue
        if len(present) != 1:
            raise ValueError(f"record {rec.recid}: several levels {present} in a tree result")
        parent = stack[lvl - 1] if lvl > 0 else total
        if lvl > 0 and parent is None:
            raise ValueError(f"record {rec.recid}: level {lvl} without a parent")
        node = Node(rec.recid, lvl, label, _raw(vfields, rec.values), parent=parent)
        if parent is not None:
            parent.children.append(node)
        stack[lvl] = node
        for k in range(lvl + 1, len(stack)):
            stack[k] = None
        nodes.append(node)
    if total is None:
        raise ValueError("no grand total row")
    return total, nodes


def leaves(nodes: list[Node], n_levels: int) -> list[Node]:
    return [n for n in nodes if n.level == n_levels - 1]


@dataclass
class FlatRow:
    recid: int
    labels: tuple[str, ...]
    raw: dict[str, str]
    line_id: int | None

    def key(self) -> tuple:
        return tuple(norm_key(s) for s in self.labels)

    def amounts(self) -> tuple:
        return tuple(round(v, 4) if v is not None else None for v in (parse_number(self.raw.get(k)) for k in AMOUNT_KEYS))


def build_flat(grid: Grid) -> list[FlatRow]:
    """Rows of a result grouped by contracts (all labels in every row + line id)."""
    gfields = [c.field for c in grid.group_columns]
    vfields = value_fields(grid)
    lid = line_id_field(grid)
    out = []
    for rec in grid.records:
        labels = tuple(rec.values.get(f, "") for f in gfields)
        if is_total_label(labels[0]) and not any(labels[1:]):
            continue
        line = rec.values.get(lid) if lid else None
        out.append(FlatRow(rec.recid, labels, _raw(vfields, rec.values), int(line) if line and line.isdigit() else None))
    return out
