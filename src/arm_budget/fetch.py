"""Data collection: catalog (forms, classifiers, documents), report queries, probes, contracts.

Everything downloaded goes to ``data/raw`` (gzip-compressed HTML/XML, PDF) and is
described by small manifests in ``data/catalog`` (versioned in git: their diff shows
what changed on the site). The build step reads only these two folders.

Steps (``python -m arm_budget <step>``):

* ``catalog``   – start page (report totals), the forms of every report for every year
                  (classifier lists with codes), PDF documents linked from the forms;
* ``fetch``     – report queries for every year: the expenditure tree (6 levels), the list
                  of expenditure lines with contracts, revenue trees by revenue type,
                  deficit (totals / all lines), the Excel exports (date the data refer to),
                  and the probes that resolve ambiguous classifier codes;
* ``contracts`` – contract pages of every expenditure line with contracts.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import time
from pathlib import Path

from . import config
from .parsers.forms import parse_form, parse_sidebar
from .parsers.grid import Grid, parse_grid
from .parsers.xls_export import parse_title
from .resolve import Classifier, needed_probes, resolve
from .site import Site, SiteError
from .tree import build_flat, build_tree
from .utils import read_gz_text, read_json, sha256_bytes, sha256_text, utc_now, write_bytes, write_gz_text, write_json

log = logging.getLogger(__name__)

SITE_JSON = config.CATALOG_DIR / "site.json"
DOCUMENTS_JSON = config.CATALOG_DIR / "documents.json"
REQUESTS_JSON = config.CATALOG_DIR / "requests.json"
PROBES_JSON = config.CATALOG_DIR / "probes.json"
CLASSIFIERS_DIR = config.CATALOG_DIR / "classifiers"
CONTRACTS_CATALOG_DIR = config.CATALOG_DIR / "contracts"


# ---------------------------------------------------------------------------
# paths and manifests
# ---------------------------------------------------------------------------

def report_path(year: int, name: str) -> Path:
    return config.REPORTS_DIR / str(year) / f"{name}.html.gz"


def export_path(year: int, name: str) -> Path:
    return config.REPORTS_DIR / str(year) / f"{name}.export.xml.gz"


def probe_path(year: int, request: str, dim: str, code: str) -> Path:
    return config.PROBES_DIR / str(year) / request / f"{dim}-{code}.html.gz"


def contract_path(year: int, line_id: int) -> Path:
    return config.CONTRACTS_DIR / str(year) / f"{line_id}.html.gz"


def classifier_path(report: str, year: int) -> Path:
    return CLASSIFIERS_DIR / f"{report}_{year}.json"


def grid_sha(grid: Grid) -> str:
    """Hash of the grid content (stable across sessions, unlike the page HTML)."""
    payload = json.dumps([[r.recid, sorted(r.values.items()), r.style] for r in grid.records], ensure_ascii=False)
    return sha256_text(payload)


def years() -> dict[int, int]:
    """Calendar year -> SITE_YEAR index, from the catalog."""
    site = read_json(SITE_JSON)
    if not site:
        raise SystemExit("data/catalog/site.json not found: run `python -m arm_budget catalog` first")
    return {int(y): int(i) for y, i in site["years"].items()}


def load_classifiers(report: config.Report, year: int) -> dict[str, Classifier]:
    data = read_json(classifier_path(report.key, year))
    if data is None:
        raise SystemExit(f"{classifier_path(report.key, year)} not found: run the catalog step")
    out = {}
    for d in report.dims:
        items = [(o["code"], o["name"]) for o in data["lists"].get(d.form_field, [])]
        out[d.key] = Classifier(d.key, items)
    return out


def load_other_years(report: config.Report, year: int) -> dict[str, Classifier]:
    """Classifier lists of all the other years of the catalog, merged (fallback for name matching)."""
    items: dict[str, dict[str, str]] = {d.key: {} for d in report.dims}
    for path in sorted(CLASSIFIERS_DIR.glob(f"{report.key}_*.json")):
        data = read_json(path)
        if data["year"] == year:
            continue
        for d in report.dims:
            for o in data["lists"].get(d.form_field, []):
                items[d.key].setdefault(o["code"], o["name"])
    return {k: Classifier(k, list(v.items())) for k, v in items.items()}


# ---------------------------------------------------------------------------
# step 1: catalog
# ---------------------------------------------------------------------------

def _check_grouping_options(report: config.Report, form) -> list[str]:
    """Compare the 'group by' options of the site with config.Report.dims; return warnings."""
    problems = []
    opts = {o.value: o.label for o in form.selects.get("site_NN1", [])}
    for d in report.dims:
        if opts.get(str(d.group_value)) != d.group_label:
            problems.append(f"{report.key}: group option {d.group_value} is {opts.get(str(d.group_value))!r}, expected {d.group_label!r}")
    if report.extra.get("contracts_group_value"):
        v = str(report.extra["contracts_group_value"])
        if opts.get(v) != report.extra["contracts_group_label"]:
            problems.append(f"{report.key}: group option {v} is {opts.get(v)!r}, expected contracts")
    return problems


def catalog(site: Site | None = None) -> None:
    site = site or Site()
    start = site.start()
    write_gz_text(config.SITE_DIR / "index.html.gz", start)
    sidebar = parse_sidebar(start)
    fetched = utc_now()

    year_index: dict[int, int] | None = None
    documents: dict[str, dict] = {}
    warnings: list[str] = []
    for report in config.REPORTS.values():
        text = site.form(report.page)
        form = parse_form(text)
        yi = {y: i for i, y in form.year_options().items()}
        if year_index is None:
            year_index = yi
        elif yi != year_index:
            warnings.append(f"{report.key}: years {yi} differ from {year_index}")
        for year, idx in sorted(yi.items()):
            extra = [("SITE_EBUDG", 0)] if report.key == "revenue" else ([("SITE_DALL", 2)] if report.key == "deficit" else [])
            text, form = site.form_for_year(report, idx, extra)
            if form.selected("SITE_YEAR") != str(idx):
                raise SiteError(f"{report.key}: year {year} not selected in the form")
            write_gz_text(config.SITE_DIR / "forms" / f"{report.key}_{year}.html.gz", text)
            if report.dims:
                warnings += _check_grouping_options(report, form)
            write_json(classifier_path(report.key, year), {
                "report": report.key, "page": report.page, "year": year, "year_index": idx, "fetched_at": fetched,
                "title": form.title,
                "select_labels": form.select_labels,
                "selects": {k: [{"value": o.value, "label": o.label} for o in v] for k, v in form.selects.items()},
                "list_titles": form.list_titles,
                "lists": {k: [{"code": o.value, "name": o.label} for o in v] for k, v in form.lists.items()},
            })
            for url, title in form.documents:
                documents.setdefault(url, {"url": url, "title_hy": title, "reports": []})
                if report.key not in documents[url]["reports"]:
                    documents[url]["reports"].append(report.key)
            log.info("catalog %s %d: %s", report.key, year, {k: len(v) for k, v in form.lists.items()})

    for doc in documents.values():
        data = site.get_bytes("/" + doc["url"])
        name = doc["url"].rsplit("/", 1)[-1]
        write_bytes(config.DOCS_RAW_DIR / name, data)
        doc.update({"file": name, "size_bytes": len(data), "sha256": sha256_bytes(data), "fetched_at": fetched})
    write_json(DOCUMENTS_JSON, sorted(documents.values(), key=lambda d: d["url"]))

    write_json(SITE_JSON, {
        "base_url": config.BASE_URL,
        "fetched_at": fetched,
        "reports": sidebar,
        "years": {str(y): i for y, i in sorted(year_index.items())},
        "warnings": warnings,
    })
    for w in warnings:
        log.warning("%s", w)
    log.info("catalog: years %s, %d documents", sorted(year_index), len(documents))


# ---------------------------------------------------------------------------
# step 2: report queries
# ---------------------------------------------------------------------------

def _group_fields(dims: tuple[config.Dimension, ...], extra: list[int] | None = None) -> list[tuple[str, str]]:
    values = [d.group_value for d in dims] + (extra or [])
    return [(f"site_NN{i}", str(v)) for i, v in enumerate(values, start=1)]


class Fetcher:
    def __init__(self, site: Site | None = None) -> None:
        self.site = site or Site()
        self.requests = {r["name"] + "@" + str(r["year"]): r for r in read_json(REQUESTS_JSON, [])}
        self.probes = {(p["year"], p["request"], p["dim"], p["code"]): p for p in read_json(PROBES_JSON, [])}

    def save_manifests(self) -> None:
        write_json(REQUESTS_JSON, sorted(self.requests.values(), key=lambda r: (r["year"], r["name"])))
        write_json(PROBES_JSON, sorted(self.probes.values(), key=lambda p: (p["year"], p["request"], p["dim"], p["code"])))

    def _record(self, year: int, name: str, report: config.Report, fields, text: str, grid: Grid,
                export_text: str | None) -> None:
        write_gz_text(report_path(year, name), text)
        as_of, title = None, None
        if export_text is not None:
            write_gz_text(export_path(year, name), export_text)
            title, d = parse_title(export_text)
            as_of = d.isoformat() if d else None
        self.requests[f"{name}@{year}"] = {
            "name": name, "report": report.key, "year": year,
            "params": [list(f) for f in fields],
            "file": str(report_path(year, name).relative_to(config.DATA_DIR)),
            "export_file": str(export_path(year, name).relative_to(config.DATA_DIR)) if export_text is not None else None,
            "export_title": title, "as_of": as_of,
            "n_records": len(grid.records), "content_sha256": grid_sha(grid), "fetched_at": utc_now(),
        }
        log.info("%s %d: %d rows%s", name, year, len(grid.records), f", as of {as_of}" if as_of else "")

    def run_query(self, year: int, name: str, report: config.Report, fields, expect_group=None,
                  export: bool = True, export_param: str | None = None) -> Grid:
        """Run a query and store its result; ``export`` also stores the Excel export of the result,
        whose title gives the date the data refer to (exports are slow for big results)."""
        text, grid = self.site.query(report, fields, expect_group)
        export_text = None
        if export:
            try:
                export_text = self.site.export(report.export, export_param)
            except SiteError as exc:
                log.warning("%s %d: export failed: %s", name, year, exc)
        self._record(year, name, report, fields, text, grid, export_text)
        return grid

    # -- probes ---------------------------------------------------------------
    def resolve_probes(self, year: int, request: str, report: config.Report, grid: Grid,
                       base_fields: list[tuple[str, str]], reuse: bool = False) -> None:
        """Fetch the probes needed to resolve the classifier codes of a tree result.

        Probes are normally re-run together with their tree (they are matched by amounts);
        ``reuse`` keeps the probes already stored for this tree and runs only the missing ones."""
        lists = load_classifiers(report, year)
        other = load_other_years(report, year)
        expect = [d.group_label for d in report.dims]
        _, nodes = build_tree(grid)
        done: dict[tuple[str, str], Grid | None] = {}
        if reuse:
            for (y, req, dim, code), p in self.probes.items():
                if y == year and req == request:
                    path = config.DATA_DIR / p["file"] if p.get("file") else None
                    done[(dim, code)] = parse_grid(read_gz_text(path)) if path and path.exists() else None
        for round_no in range(3):
            stats = resolve(nodes, report.dims, lists, done, other)
            want = needed_probes(nodes, report.dims, lists, set(done), round_no)
            log.info("%s %d: codes %s, %d probes to run (round %d)", request, year, stats, len(want), round_no + 1)
            if not want:
                break
            for dim, code in want:
                d = next(x for x in report.dims if x.key == dim)
                fields = [*base_fields, (f"{d.form_field}[]", code), *_group_fields(report.dims)]
                try:
                    text, pgrid = self.site.query(report, fields, expect, attempts=2, allow_empty=True,
                                                  read_timeout=config.HTTP_PROBE_TIMEOUT)
                except SiteError:
                    text, pgrid = None, None  # empty result: the code has no data this year
                done[(dim, code)] = pgrid
                path = probe_path(year, request, dim, code)
                if text is not None:
                    write_gz_text(path, text)
                self.probes[(year, request, dim, code)] = {
                    "year": year, "request": request, "dim": dim, "code": code,
                    "file": str(path.relative_to(config.DATA_DIR)) if text is not None else None,
                    "n_records": len(pgrid.records) if pgrid else 0,
                    "content_sha256": grid_sha(pgrid) if pgrid and pgrid.records else None, "fetched_at": utc_now(),
                }
        # forget probes of this request that were not needed this time (and their files)
        for key in [k for k in self.probes if k[0] == year and k[1] == request and (k[2], k[3]) not in done]:
            old = self.probes.pop(key)
            if old.get("file") and (config.DATA_DIR / old["file"]).exists():
                (config.DATA_DIR / old["file"]).unlink()
        stats = resolve(nodes, report.dims, lists, done, other)
        log.info("%s %d: codes resolved %s", request, year, stats)

    # -- reports ----------------------------------------------------------------
    def expenditure(self, year: int, idx: int) -> None:
        rep = config.EXPENDITURE
        expect = [d.group_label for d in rep.dims]
        base = [("SITE_YEAR", str(idx))]
        grid = self.run_query(year, "expenditure", rep, base + _group_fields(rep.dims), expect)
        self.resolve_probes(year, "expenditure", rep, grid, base)
        self.save_manifests()
        # lines with contracts: grouping by "contracts" gives a flat list with the line id (c20)
        fields = base + [("site_NN1", str(rep.extra["contracts_group_value"]))]
        self.run_query(year, "expenditure-contract-lines", rep, fields, expect, export=False)

    def revenue(self, year: int, idx: int) -> None:
        rep = config.REVENUE
        expect = [d.group_label for d in rep.dims]
        for t in rep.extra["types"]:
            base = [("SITE_YEAR", str(idx)), ("SITE_EBUDG", str(t))]
            name = f"revenue-t{t}"
            # the "as of" date is the same for all types: export only the smallest result (official grants)
            grid = self.run_query(year, name, rep, base + _group_fields(rep.dims), expect, export=t == 2)
            if t in rep.extra["fact_types"]:
                self.resolve_probes(year, name, rep, grid, base)
            self.save_manifests()

    def deficit(self, year: int, idx: int) -> None:
        rep = config.DEFICIT
        for v in rep.extra["views"]:
            fields = [("SITE_YEAR", str(idx)), ("SITE_DALL", str(v))]
            self.run_query(year, f"deficit-v{v}", rep, fields, None, export_param="<PARAM>1;</PARAM>")

    def probes_only(self, only_years: tuple[int, ...] | None = None) -> None:
        """Run the missing probes for the trees already on disk (no tree queries)."""
        for year, idx in sorted(years().items(), reverse=True):
            if only_years and year not in only_years:
                continue
            jobs = [("expenditure", config.EXPENDITURE, [("SITE_YEAR", str(idx))])]
            jobs += [(f"revenue-t{t}", config.REVENUE, [("SITE_YEAR", str(idx)), ("SITE_EBUDG", str(t))])
                     for t in config.REVENUE.extra["fact_types"]]
            for name, rep, base in jobs:
                path = report_path(year, name)
                if path.exists():
                    self.resolve_probes(year, name, rep, parse_grid(read_gz_text(path)), base, reuse=True)
                    self.save_manifests()

    def fetch(self, only_years: tuple[int, ...] | None = None, reports: tuple[str, ...] | None = None) -> None:
        for year, idx in sorted(years().items(), reverse=True):
            if only_years and year not in only_years:
                continue
            for key in reports or tuple(config.REPORTS):
                getattr(self, key)(year, idx)
                self.save_manifests()


def fetch(only_years=None, reports=None, probes_only: bool = False) -> None:
    if probes_only:
        Fetcher().probes_only(only_years)
    else:
        Fetcher().fetch(only_years, reports)


# ---------------------------------------------------------------------------
# step 3: contracts
# ---------------------------------------------------------------------------

def contract_lines(year: int) -> list[int]:
    path = report_path(year, "expenditure-contract-lines")
    if not path.exists():
        return []
    grid = parse_grid(read_gz_text(path))
    return sorted({r.line_id for r in build_flat(grid) if r.line_id})


CONTRACT_FIELDS = ["line_id", "n_contracts", "content_sha256", "fetched_at"]


def _contract_row(line: int, text: str, fetched_at: str) -> dict:
    from .parsers.contracts import parse_contracts

    _, contracts = parse_contracts(text, config.BASE_URL)
    payload = json.dumps([[c.partner, c.start_raw, c.end_raw, c.amount_raw, c.paid_raw, c.files] for c in contracts],
                         ensure_ascii=False)
    return {"line_id": line, "n_contracts": len(contracts), "content_sha256": sha256_text(payload), "fetched_at": fetched_at}


def _write_contract_manifest(path: Path, rows: dict[int, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CONTRACT_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    tmp.replace(path)


def fetch_contracts(only_years: tuple[int, ...] | None = None, refresh_years: int = 1, force: bool = False,
                    max_age_hours: float = 12) -> None:
    """Download the contract page of every expenditure line with contracts.

    Pages already on disk are kept, except for the ``refresh_years`` most recent years
    (contracts and payments of the current year change every day): their pages are
    downloaded again when older than ``max_age_hours``. The manifest
    ``data/catalog/contracts/<year>.csv`` is written every 100 pages, so an interrupted
    run continues where it stopped. Pages with thousands of contracts take minutes to render.
    """
    yi = years()
    recent = sorted(yi, reverse=True)[:refresh_years]
    site = Site()
    for year, idx in sorted(yi.items(), reverse=True):
        if only_years and year not in only_years:
            continue
        ids = contract_lines(year)
        manifest_path = CONTRACTS_CATALOG_DIR / f"{year}.csv"
        rows: dict[int, dict] = {}
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                rows = {int(r["line_id"]): r for r in csv.DictReader(f)}
        rows = {k: v for k, v in rows.items() if k in set(ids)}
        n_new = 0
        todo = []
        for line in ids:
            path = contract_path(year, line)
            if path.exists() and not force:
                age_h = (time.time() - path.stat().st_mtime) / 3600
                if year not in recent or age_h < max_age_hours:
                    if line not in rows:  # page on disk from an interrupted run
                        fetched = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).replace(microsecond=0)
                        rows[line] = _contract_row(line, read_gz_text(path), fetched.isoformat())
                    continue
            todo.append(line)
        log.info("contracts %d: %d lines, %d to download", year, len(ids), len(todo))
        for pass_no in (1, 2, 3):  # pages that hang are retried in the next pass
            failed = []
            for line in todo:
                try:
                    text = site.contracts(line, idx)
                except SiteError as exc:
                    log.warning("contracts %d/%d: %s", year, line, str(exc)[:200])
                    failed.append(line)
                    continue
                write_gz_text(contract_path(year, line), text)
                rows[line] = _contract_row(line, text, utc_now())
                n_new += 1
                if n_new % 100 == 0:
                    _write_contract_manifest(manifest_path, rows)
                    log.info("contracts %d: %d downloaded, %d failed in pass %d", year, n_new, len(failed), pass_no)
            todo = failed
            if not todo:
                break
        _write_contract_manifest(manifest_path, rows)
        log.info("contracts %d: %d lines, %d downloaded, %d failed%s", year, len(ids), n_new, len(todo),
                 " (run the step again)" if todo else "")
