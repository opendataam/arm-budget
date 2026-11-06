"""Resolve classifier codes of the nodes of a report tree.

The result grids contain only names, never codes. Codes are known from the
checkbox lists of the form (code + name, per year). The names in the grid differ
from the list in punctuation (commas, semicolons and quotes are dropped, economic
articles get a '- ' prefix), so they are compared by letters and digits only
(:func:`arm_budget.parsers.common.norm_key`).

1. **By name.** A node gets the code whose list name matches its label, if exactly one
   code matches. For the functional classification (section 2 digits -> group 4 ->
   class 6) a candidate must also start with the code of the parent node. A label that is
   not in the list of its year at all is looked up in the lists of the other years.
2. **By probe.** Some names are shared by several codes (e.g. five departments
   called «Այլ մարմիններ», two economic articles «Գործուղումների և շրջագայությունների
   ծախսեր»), some labels in the grid do not match any list name (typos, truncation).
   For those the collector runs a *probe*: the same query filtered by one candidate
   code. In the probe result, every node at the level of that classifier has that code;
   it is matched to the node of the full tree with the same labels on the path and the
   same amounts.

The same functions are used by the collector (to decide which probes to request) and
by the build (to assign the codes from the stored probes), so the build needs no network.
"""

from __future__ import annotations

import difflib
import logging
from collections import defaultdict
from dataclasses import dataclass

from . import config
from .parsers.common import norm_key
from .parsers.grid import Grid
from .tree import Node, build_tree

log = logging.getLogger(__name__)

PREFIX_DIMS = {"func_group", "func_class"}  # code starts with the parent's code
PROBE_STEPS = (5,)  # rounds: how many similar unused codes to probe for labels without a matching name


@dataclass
class Classifier:
    """Codes and names of one classifier for one year (the checkbox list of the form)."""

    dim: str
    items: list[tuple[str, str]]  # (code, name)

    def __post_init__(self):
        self.by_key: dict[str, set[str]] = defaultdict(set)
        self.names: dict[str, str] = {}
        for code, name in self.items:
            self.by_key[norm_key(name)].add(code)
            self.names[code] = name


def _filter_prefix(dim: str, node: Node, cands: set[str]) -> set[str]:
    if dim in PREFIX_DIMS and node.parent is not None and node.parent.code:
        return {c for c in cands if c.startswith(node.parent.code)}
    return cands


def resolve_by_name(nodes: list[Node], dims: tuple[config.Dimension, ...], lists: dict[str, Classifier],
                    other: dict[str, Classifier] | None = None) -> None:
    """Codes by a unique name match in the list of the year; if the name is not in that list at all,
    in the lists of the other years (``other``; the list of a year does not always contain every
    code that has data in that year)."""
    for node in nodes:  # source order: parents before children
        dim = dims[node.level].key
        key = norm_key(node.label)
        cands = _filter_prefix(dim, node, set(lists[dim].by_key.get(key, set())))
        method = "name"
        if not cands and other is not None:
            cands = _filter_prefix(dim, node, set(other[dim].by_key.get(key, set())))
            method = "name_other_year"
        node.candidates = cands
        if len(cands) == 1:
            node.code, node.method = next(iter(cands)), method
        else:
            node.code, node.method = None, None


def apply_probes(nodes: list[Node], dims: tuple[config.Dimension, ...], probes: dict[tuple[str, str], Grid | None]) -> int:
    """Assign codes from probe results. Returns the number of nodes resolved."""
    level_of = {d.key: i for i, d in enumerate(dims)}
    sig_code: dict[tuple, set[str]] = defaultdict(set)
    for (dim, code), grid in probes.items():
        if grid is None or not grid.records:
            continue
        try:
            _, pnodes = build_tree(grid)
        except ValueError as exc:
            log.warning("probe %s=%s: %s", dim, code, exc)
            continue
        lvl = level_of[dim]
        for pn in pnodes:
            if pn.level == lvl:
                sig_code[pn.signature()].add(code)
    n = 0
    for node in nodes:
        if node.code is not None:
            continue
        codes = sig_code.get(node.signature(), set())
        dim = dims[node.level].key
        codes = {c for c in codes if level_of[dim] == node.level}
        if len(codes) == 1:
            node.code, node.method = next(iter(codes)), "probe"
            n += 1
    return n


def _resolved_codes(nodes: list[Node], dim_level: int) -> set[str]:
    return {n.code for n in nodes if n.level == dim_level and n.code}


def needed_probes(nodes: list[Node], dims: tuple[config.Dimension, ...], lists: dict[str, Classifier],
                  done: set[tuple[str, str]], round_no: int = 0) -> list[tuple[str, str]]:
    """Probes (dimension key, code) that could resolve the nodes still without a code."""
    want: dict[tuple[str, str], None] = {}
    for lvl, d in enumerate(dims):
        clf = lists[d.key]
        unresolved = [n for n in nodes if n.level == lvl and n.code is None]
        if not unresolved:
            continue
        used = _resolved_codes(nodes, lvl)
        for node in unresolved:
            if len(node.candidates) > 1:
                cands = sorted(node.candidates)
            elif round_no >= len(PROBE_STEPS):
                continue  # give up: the label has no counterpart in the classifier lists
            else:
                pool = [c for c, _ in clf.items if c not in used]
                if d.key in PREFIX_DIMS and node.parent is not None and node.parent.code:
                    pool = [c for c in pool if c.startswith(node.parent.code)]
                # codes listed without a name are the first suspects (the list of a year has a few of them)
                nameless = [c for c in pool if not norm_key(clf.names[c])]
                key = norm_key(node.label)
                named = [c for c in pool if norm_key(clf.names[c])]
                named.sort(key=lambda c: -difflib.SequenceMatcher(None, key, norm_key(clf.names[c])).ratio())
                cands = nameless + named[: PROBE_STEPS[round_no]]
            for c in cands:
                if (d.key, c) not in done:
                    want[(d.key, c)] = None
    return list(want)


def resolve(nodes: list[Node], dims: tuple[config.Dimension, ...], lists: dict[str, Classifier],
            probes: dict[tuple[str, str], Grid | None], other: dict[str, Classifier] | None = None) -> dict[str, int]:
    """Resolve codes by name, then by the probes. Returns counts by method."""
    resolve_by_name(nodes, dims, lists, other)
    # A probe may resolve a parent, which narrows the candidates of its children (prefix rule):
    for _ in range(3):
        if not apply_probes(nodes, dims, probes):
            break
        for node in nodes:
            if node.code is None and node.parent is not None:
                cands = _filter_prefix(dims[node.level].key, node, node.candidates or
                                       set(lists[dims[node.level].key].by_key.get(norm_key(node.label), set())))
                if len(cands) == 1:
                    node.code, node.method = next(iter(cands)), "name"
    stats: dict[str, int] = defaultdict(int)
    for n in nodes:
        stats[n.method or "unresolved"] += 1
    return dict(stats)
