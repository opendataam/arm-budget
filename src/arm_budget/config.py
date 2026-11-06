"""Project-wide constants: paths, the source site, report definitions, HTTP settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SITE_DIR = RAW_DIR / "site"            # start page, form pages per report and year
DOCS_RAW_DIR = RAW_DIR / "documents"   # PDF documents linked from the forms
REPORTS_DIR = RAW_DIR / "reports"      # report results (w2ui grids) and Excel exports
PROBES_DIR = RAW_DIR / "probes"        # filtered queries used to resolve classifier codes
CONTRACTS_DIR = RAW_DIR / "contracts"  # contract pages per expenditure line
CATALOG_DIR = DATA_DIR / "catalog"     # small JSON/CSV manifests (committed to git)
TRANSLATIONS_DIR = DATA_DIR / "translations"  # hy -> en / ru dictionaries (committed to git)
PENDING_DIR = TRANSLATIONS_DIR / "pending"    # strings still to translate (not in git)
SQL_DIR = ROOT / "sql"
DUCKDB_PATH = DATA_DIR / "arm_budget.duckdb"
RELEASE_DIR = DATA_DIR / "release"     # packed data snapshots (not in git)

# GitHub repository whose releases carry the data snapshots (override: env ARM_BUDGET_REPO)
GITHUB_REPO = "opendataam/arm-budget"

BASE_URL = "https://budget.minfin.am:82"

USER_AGENT = "arm-budget-collector/0.1 (open data research; python-requests)"
HTTP_CONNECT_TIMEOUT = 30
HTTP_TIMEOUT = 120      # read timeout of ordinary requests
HTTP_RESULT_TIMEOUT = 400  # read timeout of result pages: the full expenditure tree takes 30-300 s to render
HTTP_PROBE_TIMEOUT = 60    # read timeout of probes (small filtered results; the server sometimes never answers)
HTTP_CONTRACT_TIMEOUT = 45  # read timeout of contract pages (the largest, ~3 000 contracts, renders in ~20 s)
HTTP_RETRIES = 5
HTTP_DELAY = 0.5        # seconds between requests (be polite)
HTTP_IDLE_RECONNECT = 5  # seconds of idleness after which the keep-alive connection is not reused

LANGS = ("en", "hy", "ru")


@dataclass(frozen=True)
class Dimension:
    """A classifier the site lets you filter (checkbox list) and group by (site_NN select)."""

    key: str          # name used in the database (dim_<table>, <key>_code columns)
    form_field: str   # checkbox list name on the form: mid / grp / sgrp / cls / prog / sub / acc
    group_value: int  # value of the option in the site_NN<i> "group by" selects
    group_label: str  # Armenian label of that option (checked against the site; changes are reported)
    table: str        # dimension table


@dataclass(frozen=True)
class Report:
    key: str                 # expenditure / revenue / deficit
    page: str                # param.php page code
    popup: str | None        # Popup.php page with the result grid (None: the grid is on the form page)
    export: str              # xml/xmlopen.php page of the Excel (SpreadsheetML) export
    title_hy: str
    dims: tuple[Dimension, ...] = field(default_factory=tuple)
    extra: dict = field(default_factory=dict)


EXPENDITURE = Report(
    key="expenditure", page="site_b", popup="SITE_BG", export="SITE_B_XLS", title_hy="Ծախսեր",
    dims=(
        Dimension("func_section", "grp", 1, "Բաժին", "dim_functional"),
        Dimension("func_group", "sgrp", 2, "Խումբ", "dim_functional"),
        Dimension("func_class", "cls", 3, "Դաս", "dim_functional"),
        Dimension("program", "prog", 4, "Ծրագիր", "dim_program"),
        Dimension("department", "mid", 5, "Գերատեսչական դասակարգում", "dim_department"),
        Dimension("economic", "sub", 6, "Հոդված", "dim_economic"),
    ),
    # "group by contracts" adds the line id (column c20) that opens the contract popup SITE_C
    extra={"contracts_group_value": 7, "contracts_group_label": "Պայմանագրեր", "contract_popup": "SITE_C"},
)

REVENUE = Report(
    key="revenue", page="site_d", popup="SITE_DG", export="SITE_D_XLS", title_hy="Եկամուտներ",
    dims=(
        Dimension("rev_section", "grp", 1, "Բաժին", "dim_revenue_section"),
        Dimension("rev_group", "sgrp", 2, "Խումբ", "dim_revenue_group"),
        Dimension("department", "mid", 3, "Գերատեսչական դասակարգում", "dim_department"),
        Dimension("rev_account", "acc", 4, "Հաշիվ", "dim_revenue_account"),
    ),
    # SITE_EBUDG: 0 = all revenues (detail rows carry no plan!), 1 = taxes and duties,
    # 2 = official grants, 3 = other revenues. Facts are built from 1-3, 0 is kept for checks.
    extra={"types": {0: "Եկամուտներ", 1: "Հարկեր և տուրքեր", 2: "Պաշտոնական դրամաշնորհներ", 3: "Այլ եկամուտներ"},
           "fact_types": (1, 2, 3)},
)

DEFICIT = Report(
    key="deficit", page="site_l", popup=None, export="SITE_L_XLS", title_hy="Դեֆիցիտ",
    # SITE_DALL: 1 = totals only, 2 = all lines
    extra={"views": {1: "Հանրագումարները", 2: "Բոլորը"}},
)

REPORTS: dict[str, Report] = {r.key: r for r in (EXPENDITURE, REVENUE, DEFICIT)}

# The 12 value columns of every report: (period, measure) in the order of the grid.
# Plans and executed amounts are cumulative from the beginning of the year; % = actual / plan.
PERIODS = ("q1", "h1", "m9", "year")
VALUE_COLUMNS = [(p, m) for p in PERIODS for m in ("plan", "actual", "pct")]

# Links to PDF documents on the form pages are collected by the catalog step.
DOCUMENT_PREFIX = "xml/"
