"""Build the DuckDB database from ``data/raw`` and ``data/catalog`` (no network).

The database is rebuilt from scratch on every run, into a temporary file that
replaces ``data/arm_budget.duckdb`` at the end, so the build is deterministic and
atomic. Steps:

1. schema (sql/schema.sql);
2. metadata: languages, reports, years, requests, probes, documents, interface labels;
3. dimensions from the classifier lists of every report and year (data/catalog/classifiers),
   with the translations of data/translations;
4. every report grid: lossless cells (raw_*), tree nodes with resolved codes (stg_report_node),
   leaves as facts (fact_expenditure, fact_revenue), deficit lines (fact_deficit);
5. lines with contracts -> fact_expenditure.contract_line_id; contract pages -> fact_contract*;
6. views (sql/views.sql) and data quality checks (sql/qc.sql).
"""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import duckdb
import pandas as pd

from . import config, reference
from .fetch import (
    CONTRACTS_CATALOG_DIR,
    DOCUMENTS_JSON,
    PROBES_JSON,
    REQUESTS_JSON,
    SITE_JSON,
    classifier_path,
    contract_path,
    load_other_years,
)
from .parsers.common import clean_label, norm_key, parse_decimal
from .parsers.contracts import parse_contracts
from .parsers.deficit import classify
from .parsers.forms import parse_form
from .parsers.grid import Grid, parse_grid
from .resolve import Classifier, resolve, resolve_by_name
from .translations import Dictionary
from .translit import partner_name
from .tree import AMOUNT_KEYS, build_flat, build_tree, value_fields
from .utils import read_gz_text, read_json

log = logging.getLogger(__name__)

AMOUNT_COLS = [f"{k}_kamd" for k in AMOUNT_KEYS]  # q1_plan_kamd, q1_actual_kamd, ...


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def insert(con: duckdb.DuckDBPyConnection, table: str, records: list[dict] | pd.DataFrame) -> int:
    df = records if isinstance(records, pd.DataFrame) else pd.DataFrame.from_records(records)
    if df.empty:
        log.warning("table %s: nothing to insert", table)
        return 0
    cols = [r[0] for r in con.execute(f"DESCRIBE {table}").fetchall()]
    df = df[[c for c in df.columns if c in cols]]
    con.register("_df", df)
    con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM _df")
    con.unregister("_df")
    log.info("table %-24s +%d rows", table, len(df))
    return len(df)


def amounts(raw: dict[str, str]) -> dict[str, str | None]:
    """Amount cells as exact decimal strings (DuckDB casts them to DECIMAL on insert)."""
    out = {}
    for k, col in zip(AMOUNT_KEYS, AMOUNT_COLS):
        v = parse_decimal(raw.get(k))
        out[col] = None if v is None else str(v)
    return out


def load_grid(rel: str) -> tuple[str, Grid]:
    text = read_gz_text(config.DATA_DIR / rel)
    grid = parse_grid(text)
    if grid is None:
        raise ValueError(f"{rel}: no grid")
    return text, grid


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------

def load_meta(con, requests: list[dict], dic: Dictionary) -> dict[int, int]:
    site = read_json(SITE_JSON)
    insert(con, "meta_language", [{"lang": a, "name_en": b, "name_native": c} for a, b, c in reference.LANGUAGES])
    insert(con, "meta_report", [
        {"report": k, "page": config.REPORTS[k].page, "title_hy": hy, "title_en": en, "title_ru": ru, "fact_table": t}
        for k, (hy, en, ru, t) in reference.REPORTS.items()])
    years = {int(y): int(i) for y, i in site["years"].items()}
    as_of = {r["year"]: r["as_of"] for r in requests if r["name"] == "expenditure"}
    rows = []
    for y, i in years.items():
        d = as_of.get(y)
        rows.append({"year": y, "year_index": i, "as_of_date": d,
                     "is_complete": bool(d) and d[5:7] == "12" and int(d[8:10]) >= 25})
    insert(con, "meta_year", rows)
    current = max(years)
    insert(con, "meta_site_total", [
        {"report": next((k for k, r in config.REPORTS.items() if r.page == s["page"]), s["page"]),
         "label_hy": s["label"], "total_kamd": s["total_kamd"], "year": current, "fetched_at": site["fetched_at"]}
        for s in site["reports"]])
    req_rows = []
    for r in requests:
        name = r["name"]
        req_rows.append({
            "request_id": f"{name}@{r['year']}", "name": name, "report": r["report"], "year": r["year"],
            "revenue_type": int(name.rsplit("-t", 1)[1]) if name.startswith("revenue-t") else None,
            "deficit_view": int(name.rsplit("-v", 1)[1]) if name.startswith("deficit-v") else None,
            "params": json.dumps(r["params"], ensure_ascii=False), "file": r["file"], "export_file": r.get("export_file"),
            "export_title": r.get("export_title"), "as_of_date": r.get("as_of"), "n_records": r["n_records"],
            "content_sha256": r["content_sha256"], "fetched_at": r["fetched_at"]})
    insert(con, "meta_request", req_rows)
    insert(con, "meta_probe", [{k: p[k] for k in ("year", "request", "dim", "code", "file", "n_records", "fetched_at")}
                               for p in read_json(PROBES_JSON, [])])
    docs = []
    for d in read_json(DOCUMENTS_JSON, []):
        en, ru = reference.DOCUMENTS.get(d["file"], (None, None))
        docs.append({"file": d["file"], "url": f"{config.BASE_URL}/{d['url']}", "title_hy": d["title_hy"], "title_en": en,
                     "title_ru": ru, "reports": ",".join(d["reports"]), "size_bytes": d["size_bytes"], "sha256": d["sha256"],
                     "fetched_at": d["fetched_at"]})
    insert(con, "meta_document", docs)
    insert(con, "dim_period", [
        {"period": p, "months": m, "sort": s, "label_hy": hy, "label_en": en, "label_ru": ru}
        for p, (m, s, hy, en, ru) in reference.PERIODS.items()])
    insert(con, "dim_revenue_type", [
        {"revenue_type": t, "name_hy": hy, "name_en": en, "name_ru": ru} for t, (hy, en, ru) in reference.REVENUE_TYPES.items()])
    return years


def load_labels(con, dic: Dictionary) -> None:
    """Interface labels of the site (form fields, list titles, options, column captions) with translations."""
    seen: dict[tuple[str, str], str] = {}
    for report in config.REPORTS.values():
        for p in sorted((config.CATALOG_DIR / "classifiers").glob(f"{report.key}_*.json")):
            data = read_json(p)
            for k, v in data["select_labels"].items():
                seen[("field", k)] = v
            for k, v in data["list_titles"].items():
                seen[("list", f"{report.key}.{k}")] = v
            for sel, opts in data["selects"].items():
                if sel == "SITE_YEAR":
                    continue
                for o in opts:
                    seen[("option", f"{report.key}.{sel.split('_NN')[0] if '_NN' in sel else sel}.{o['value']}")] = o["label"]
    for row in con.execute("SELECT DISTINCT field, caption FROM raw_grid_cell r JOIN meta_request q USING (request_id) "
                           "WHERE caption IS NOT NULL").fetchall():
        seen[("column", row[1])] = row[1]
    rows = []
    for (ctx, key), hy in sorted(seen.items()):
        hy = clean_label(hy) or hy
        rows.append({"context": ctx, "key": key, "hy": hy, "en": dic.get("labels", hy, "en"), "ru": dic.get("labels", hy, "ru")})
    insert(con, "meta_label", rows)


# ---------------------------------------------------------------------------
# dimensions
# ---------------------------------------------------------------------------

def load_classifiers(years: dict[int, int]) -> dict[tuple[str, int], dict[str, Classifier]]:
    """(report, year) -> dimension key -> Classifier (codes and names of that year)."""
    out = {}
    for report in config.REPORTS.values():
        if not report.dims:
            continue
        for year in years:
            data = read_json(classifier_path(report.key, year))
            if data is None:
                continue
            out[(report.key, year)] = {
                d.key: Classifier(d.key, [(o["code"], clean_label(o["name"]) or "") for o in data["lists"].get(d.form_field, [])])
                for d in report.dims}
    return out


def load_dims(con, classifiers, dic: Dictionary) -> None:
    names = []
    latest: dict[str, dict[str, tuple[int, str]]] = defaultdict(dict)   # dim -> code -> (year, name)
    first: dict[str, dict[str, int]] = defaultdict(dict)
    reports_of: dict[str, set[str]] = defaultdict(set)                   # department code -> reports
    for (report, year), dims in sorted(classifiers.items()):
        for dim, clf in dims.items():
            for code, name in clf.items:
                names.append({"report": report, "dim": dim, "code": code, "year": year, "name_hy": name})
                prev = latest[dim].get(code)
                # the latest year wins; within a year the expenditure list wins (more complete names)
                if prev is None or year > prev[0]:
                    latest[dim][code] = (year, name)
                first[dim][code] = min(first[dim].get(code, year), year)
                if dim == "department":
                    reports_of[code].add(report)
    insert(con, "dim_name", pd.DataFrame(names).drop_duplicates(["report", "dim", "code", "year"]))

    def rows(dim: str) -> list[dict]:
        ctx = reference.DIMS[dim][1]
        out = []
        for code, (year, name) in sorted(latest[dim].items()):
            out.append({"code": code, "name_hy": name, "name_en": dic.get(ctx, name, "en"), "name_ru": dic.get(ctx, name, "ru"),
                        "first_year": first[dim][code], "last_year": year})
        return out

    func = []
    for dim in ("func_section", "func_group", "func_class"):
        for r in rows(dim):
            level, level_name = reference.FUNCTIONAL_LEVELS[len(r["code"])]
            func.append({**r, "level": level, "level_name": level_name, "parent_code": r["code"][:-2] or None})
    insert(con, "dim_functional", func)
    insert(con, "dim_program", rows("program"))
    insert(con, "dim_department", [{**r, "in_expenditure": "expenditure" in reports_of[r["code"]],
                                    "in_revenue": "revenue" in reports_of[r["code"]]} for r in rows("department")])
    insert(con, "dim_economic", [{**r, "class_code": r["code"][:1], "category_code": r["code"][:2], "group_code": r["code"][:3]}
                                 for r in rows("economic")])
    insert(con, "dim_economic_level", [
        {"code": c, "level": lvl, "level_name": reference.ECONOMIC_LEVEL_NAMES[lvl], "parent_code": c[:-1] or None,
         "name_hy": hy, "name_en": en, "name_ru": ru} for c, (lvl, hy, en, ru) in reference.ECONOMIC_LEVELS.items()])
    insert(con, "dim_revenue_section", rows("rev_section"))
    insert(con, "dim_revenue_group", rows("rev_group"))
    insert(con, "dim_revenue_account", rows("rev_account"))
    insert(con, "dim_translation", pd.DataFrame(dic.records(), columns=["context", "hy", "en", "ru"])
           .drop_duplicates(["context", "hy"]))


# ---------------------------------------------------------------------------
# report grids
# ---------------------------------------------------------------------------

def raw_cells(request_id: str, grid: Grid) -> tuple[list[dict], list[dict]]:
    captions = {c.field: c.caption for c in grid.columns}
    cells, rows = [], []
    for rec in grid.records:
        rows.append({"request_id": request_id, "recid": rec.recid, "style": rec.style})
        for f, v in rec.values.items():
            if v != "":
                cells.append({"request_id": request_id, "recid": rec.recid, "field": f, "caption": captions.get(f), "value": v})
    return cells, rows


def probes_for(year: int, request: str) -> dict[tuple[str, str], Grid | None]:
    out = {}
    for p in read_json(PROBES_JSON, []):
        if p["year"] != year or p["request"] != request:
            continue
        grid = None
        if p.get("file"):
            path = config.DATA_DIR / p["file"]
            if path.exists():
                grid = parse_grid(read_gz_text(path))
        out[(p["dim"], p["code"])] = grid
    return out


def process_tree(request_id: str, req: dict, report: config.Report, lists: dict[str, Classifier], grid: Grid,
                 with_probes: bool) -> tuple[list[dict], list[dict]]:
    """(stg_report_node rows, leaf rows with codes)."""
    total, nodes = build_tree(grid)
    other = load_other_years(report, req["year"])
    if with_probes:
        stats = resolve(nodes, report.dims, lists, probes_for(req["year"], req["name"]), other)
    else:
        resolve_by_name(nodes, report.dims, lists, other)
        stats = None
    if stats:
        log.info("%s: codes %s", request_id, stats)
    stg = []
    for n in [total, *nodes]:
        stg.append({"request_id": request_id, "recid": n.recid, "year": req["year"], "level": n.level,
                    "dim": report.dims[n.level].key if n.level >= 0 else None, "label_hy": n.label.strip(),
                    "parent_recid": n.parent.recid if n.parent is not None else None, "code": n.code,
                    "code_method": n.method, "is_leaf": n.level == len(report.dims) - 1, **amounts(n.raw)})
    leaves = []
    for line_no, n in enumerate([x for x in nodes if x.level == len(report.dims) - 1], start=1):
        row = {"year": req["year"], "line_no": line_no, "request_id": request_id, "recid": n.recid, "_node": n, **amounts(n.raw)}
        for p in n.path():
            row[f"{report.dims[p.level].key}_code"] = p.code
        leaves.append(row)
    return stg, leaves


def unallocated(total: dict, leaves: list[dict], revenue_type: int) -> list[dict]:
    """A row with the part of the grand total that is not distributed to the accounts.

    Revenue plans are mostly set for the revenue type as a whole: the plans of the accounts
    add up to a small part of the total plan. The difference is stored as one row per year
    and type with ``line_kind = 'unallocated'`` and no codes, so that sums over fact_revenue
    equal the totals published by the site."""
    row = {"year": total["year"], "revenue_type": revenue_type, "line_kind": "unallocated",
           "line_no": len(leaves) + 1, "request_id": total["request_id"], "recid": total["recid"]}
    nonzero = False
    for col in AMOUNT_COLS:
        tot = Decimal(total[col] or 0)
        diff = tot - sum((Decimal(x[col] or 0) for x in leaves), Decimal(0))
        row[col] = str(diff)
        nonzero |= diff != 0
    return [row] if nonzero else []


def link_contract_lines(exp_leaves: list[dict], flat_grid: Grid) -> int:
    """Set contract_line_id of the expenditure lines from the result grouped by contracts."""
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for row in exp_leaves:
        by_key[row["_node"].key()].append(row)
    n = 0
    for fr in build_flat(flat_grid):
        cands = by_key.get(fr.key(), [])
        if len(cands) > 1:  # same labels on the path: tell the lines apart by the amounts
            cands = [c for c in cands if c["_node"].amounts() == fr.amounts()] or cands
        if len(cands) == 1 and fr.line_id:
            cands[0]["contract_line_id"] = fr.line_id
            n += 1
        else:
            log.warning("contract line %s (%s): %d matching expenditure lines", fr.line_id, fr.labels[-1][:40], len(cands))
    return n


def load_reports(con, requests: list[dict], classifiers, dic: Dictionary) -> None:
    cells, rows, stg = [], [], []
    exp_leaves: dict[int, list[dict]] = {}
    rev_rows, def_rows = [], []
    flat: dict[int, Grid] = {}
    deficit_totals: dict[int, set[str]] = defaultdict(set)
    deficit_all: dict[int, tuple[str, Grid]] = {}
    for req in sorted(requests, key=lambda r: (r["year"], r["name"])):
        request_id = f"{req['name']}@{req['year']}"
        _, grid = load_grid(req["file"])
        c, r = raw_cells(request_id, grid)
        cells += c
        rows += r
        name, year = req["name"], req["year"]
        if name == "expenditure":
            s, leaves = process_tree(request_id, req, config.EXPENDITURE, classifiers[("expenditure", year)], grid, True)
            stg += s
            exp_leaves[year] = leaves
        elif name == "expenditure-contract-lines":
            flat[year] = grid
        elif name.startswith("revenue-t"):
            t = int(name.rsplit("-t", 1)[1])
            fact = t in config.REVENUE.extra["fact_types"]
            s, leaves = process_tree(request_id, req, config.REVENUE, classifiers[("revenue", year)], grid, fact)
            stg += s
            if fact:
                rev_rows += [{**x, "revenue_type": t, "line_kind": "line"} for x in leaves]
                rev_rows += unallocated(s[0], leaves, t)
        elif name == "deficit-v1":
            vf = value_fields(grid)
            deficit_totals[year] = {norm_key(rec.values.get("c2", "")) for rec in grid.records}
        elif name == "deficit-v2":
            deficit_all[year] = (request_id, grid)
    for year, leaves in exp_leaves.items():
        if year in flat:
            n = link_contract_lines(leaves, flat[year])
            log.info("expenditure %d: %d lines linked to contracts", year, n)
    for year, (request_id, grid) in deficit_all.items():
        vf = value_fields(grid)
        label_field = grid.columns[0].field
        lines = classify([rec.values.get(label_field, "") for rec in grid.records])
        for rec, ln in zip(grid.records, lines):
            raw = {k: rec.values.get(f, "") for k, f in zip([*AMOUNT_KEYS_ALL], vf)}
            def_rows.append({
                "year": year, "line_no": ln.line_no, "label_hy": ln.label, "label_en": dic.get("deficit", ln.label, "en"),
                "label_ru": dic.get("deficit", ln.label, "ru"), "item_code": ln.item_code, "row_kind": ln.kind,
                "level": ln.level, "parent_line_no": ln.parent, "note_hy": ln.note, "indent": ln.indent,
                "in_totals_view": norm_key(rec.values.get(label_field, "")) in deficit_totals.get(year, set()),
                "is_highlighted": bool(rec.style), "request_id": request_id, "recid": rec.recid, **amounts(raw)})
    insert(con, "raw_grid_row", rows)
    insert(con, "raw_grid_cell", cells)
    insert(con, "stg_report_node", stg)
    insert(con, "fact_expenditure", [{k: v for k, v in x.items() if k != "_node"} for ls in exp_leaves.values() for x in ls])
    insert(con, "fact_revenue", [{k: v for k, v in x.items() if k != "_node"} for x in rev_rows])
    insert(con, "fact_deficit", def_rows)
    fill_empty_names(con, dic)


def fill_empty_names(con, dic: Dictionary) -> None:
    """Codes listed without a name on the form get the label of the result grid (resolved by a probe)."""
    for dim, (table, ctx) in reference.DIMS.items():
        rows = con.execute(f"""
            SELECT d.code, any_value(n.label_hy ORDER BY n.year DESC) FROM {table} d
            JOIN stg_report_node n ON n.code = d.code AND n.dim = ?
            WHERE coalesce(d.name_hy, '') = '' GROUP BY d.code""", [dim]).fetchall()
        for code, label in rows:
            con.execute(f"UPDATE {table} SET name_hy = ?, name_en = ?, name_ru = ? WHERE code = ?",
                        [label, dic.get(ctx, label, "en"), dic.get(ctx, label, "ru"), code])
            log.info("%s %s: empty name in the classifier list, taken from the grid", table, code)


AMOUNT_KEYS_ALL = [f"{p}_{m}" for p, m in config.VALUE_COLUMNS]


# ---------------------------------------------------------------------------
# contracts
# ---------------------------------------------------------------------------

def load_contracts(con, years: dict[int, int]) -> None:
    contracts, files = [], []
    for year in sorted(years):
        manifest = CONTRACTS_CATALOG_DIR / f"{year}.csv"
        if not manifest.exists():
            continue
        with open(manifest, encoding="utf-8") as f:
            lines = [int(r["line_id"]) for r in csv.DictReader(f)]
        for line in lines:
            path = contract_path(year, line)
            if not path.exists():
                log.warning("contracts %d/%d: page missing", year, line)
                continue
            _, items = parse_contracts(read_gz_text(path), config.BASE_URL)
            for c in items:
                contracts.append({
                    "year": year, "contract_line_id": line, "seq": c.seq, "partner_hy": c.partner,
                    "partner_en": partner_name(c.partner, "en"), "partner_ru": partner_name(c.partner, "ru"),
                    "start_date": c.start_date, "end_date": c.end_date,
                    "amount_kamd": None if parse_decimal(c.amount_raw) is None else str(parse_decimal(c.amount_raw)),
                    "paid_kamd": None if parse_decimal(c.paid_raw) is None else str(parse_decimal(c.paid_raw)),
                    "n_files": len(c.files)})
                for k, (url, text) in enumerate(c.files, start=1):
                    host = url.split("/")[2] if "://" in url else None
                    files.append({"year": year, "contract_line_id": line, "seq": c.seq, "file_no": k, "url": url,
                                  "host": host, "link_text": text})
    insert(con, "fact_contract", contracts)
    insert(con, "fact_contract_file", files)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def run_sql(con, path: Path) -> None:
    con.execute(path.read_text(encoding="utf-8"))


def build(db_path: str | None = None) -> Path:
    out = Path(db_path) if db_path else config.DUCKDB_PATH
    tmp = out.with_name(out.stem + ".building.duckdb")
    for p in (tmp, tmp.with_suffix(".duckdb.wal")):
        if p.exists():
            p.unlink()
    requests = read_json(REQUESTS_JSON)
    if not requests:
        raise SystemExit("data/catalog/requests.json not found: run `python -m arm_budget fetch` (or `make download-raw`)")
    dic = Dictionary()
    con = duckdb.connect(str(tmp))
    run_sql(con, config.SQL_DIR / "schema.sql")
    years = load_meta(con, requests, dic)
    classifiers = load_classifiers(years)
    load_dims(con, classifiers, dic)
    load_reports(con, requests, classifiers, dic)
    load_labels(con, dic)
    load_contracts(con, years)
    run_sql(con, config.SQL_DIR / "views.sql")
    run_sql(con, config.SQL_DIR / "qc.sql")
    for name, status, n in con.execute("SELECT check_name, status, n_issues FROM qc_summary ORDER BY 1").fetchall():
        (log.warning if status == "warn" else log.info)("qc %-24s %-5s %s", name, status, n)
    con.execute("CHECKPOINT")
    con.close()
    tmp.replace(out)
    log.info("database written to %s", out)
    return out


__all__ = ["build", "parse_form"]
