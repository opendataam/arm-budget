"""Translation dictionaries Armenian -> English / Russian.

The dictionaries are CSV files in ``data/translations/<context>.csv`` with the columns
``hy,en,ru`` (UTF-8). They are versioned in git and loaded by the build into
``dim_translation``; names are looked up by the Armenian text (compared with
:func:`norm_key`, so punctuation and case differences do not matter).

Contexts: ``functional``, ``program``, ``department``, ``economic``, ``revenue``
(revenue sections, groups and accounts), ``deficit`` (lines of the deficit report),
``labels`` (interface of the site, report and period names, document titles).

Workflow for new names (e.g. after a new budget year appears on the site)::

    python -m arm_budget build          # names without a translation are listed in qc_missing_translation
    python -m arm_budget translations   # writes them to data/translations/pending/<context>-<n>.csv
    # fill the en and ru columns (by hand or with a machine translation, then review)
    python -m arm_budget translations --merge
    python -m arm_budget build
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from . import config
from .parsers.common import norm_key

log = logging.getLogger(__name__)

CONTEXTS = ("functional", "program", "department", "economic", "revenue", "deficit", "labels")
FIELDS = ["hy", "en", "ru"]


def path(context: str) -> Path:
    return config.TRANSLATIONS_DIR / f"{context}.csv"


def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return [{k: (r.get(k) or "").strip() for k in FIELDS} for r in csv.DictReader(f)]


def write_csv(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


class Dictionary:
    """All translations, looked up by context and normalised Armenian text."""

    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {c: read_csv(path(c)) for c in CONTEXTS}
        self.index: dict[tuple[str, str], dict] = {}
        self.any: dict[str, dict] = {}
        for c, rows in self.rows.items():
            for r in rows:
                if r["hy"] and (r["en"] or r["ru"]):
                    k = norm_key(r["hy"])
                    self.index[(c, k)] = r
                    self.any.setdefault(k, r)

    def get(self, context: str, hy: str | None, lang: str) -> str | None:
        if not hy:
            return None
        k = norm_key(hy)
        r = self.index.get((context, k)) or self.any.get(k)
        return (r[lang] or None) if r else None

    def records(self) -> list[tuple[str, str, str | None, str | None]]:
        return [(c, r["hy"], r["en"] or None, r["ru"] or None) for c, rows in self.rows.items() for r in rows if r["hy"]]


def write_pending(batch_size: int = 150, db_path: Path | None = None) -> None:
    """Write the names without a translation (qc_missing_translation) to data/translations/pending."""
    import duckdb

    con = duckdb.connect(str(db_path or config.DUCKDB_PATH), read_only=True)
    rows = con.execute("SELECT context, hy FROM qc_missing_translation ORDER BY context, hy").fetchall()
    con.close()
    config.PENDING_DIR.mkdir(parents=True, exist_ok=True)
    for old in config.PENDING_DIR.glob("*.csv"):
        old.unlink()
    by_ctx: dict[str, list[str]] = {}
    for ctx, hy in rows:
        by_ctx.setdefault(ctx, []).append(hy)
    n_files = 0
    for ctx, items in by_ctx.items():
        for i in range(0, len(items), batch_size):
            n_files += 1
            write_csv(config.PENDING_DIR / f"{ctx}-{i // batch_size + 1:03d}.csv",
                      [{"hy": h, "en": "", "ru": ""} for h in items[i:i + batch_size]])
    log.info("%d names without translation -> %d files in %s", len(rows), n_files, config.PENDING_DIR)


def merge_pending() -> None:
    """Merge the filled rows of data/translations/pending/*.csv into the dictionaries."""
    files = sorted(config.PENDING_DIR.glob("*.csv"))
    added: dict[str, int] = {}
    for f in files:
        ctx = f.stem.rsplit("-", 1)[0]
        if ctx not in CONTEXTS:
            log.warning("%s: unknown context %s", f, ctx)
            continue
        new = [r for r in read_csv(f) if r["hy"] and r["en"] and r["ru"]]
        merge_rows(ctx, new)
        added[ctx] = added.get(ctx, 0) + len(new)
        if len(new) == len(read_csv(f)):
            f.unlink()
    log.info("merged: %s", added)


def merge_rows(context: str, new: list[dict]) -> None:
    rows = {norm_key(r["hy"]): r for r in read_csv(path(context))}
    for r in new:
        rows[norm_key(r["hy"])] = {k: r[k] for k in FIELDS}
    write_csv(path(context), sorted(rows.values(), key=lambda r: r["hy"]))
