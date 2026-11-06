"""Generate docs/data_dictionary.md (from the comments stored in the DuckDB catalog), docs/<lang>/inventory.md
and the results table of docs/<lang>/data_quality.md (between the QC_RESULTS markers)."""

from __future__ import annotations

import logging

import duckdb

from . import config

log = logging.getLogger(__name__)

PREFIX_TITLES = [
    ("meta_", "Metadata / provenance"),
    ("dim_", "Dimensions (classifiers)"),
    ("fact_", "Facts"),
    ("stg_", "Staging (report trees)"),
    ("raw_", "Raw cells"),
    ("qc_", "Data quality"),
    ("v_", "Views"),
]


def _md(s) -> str:
    return "" if s is None else str(s).replace("|", "\\|").replace("\n", " ")


INVENTORY_TEXT = {
    "en": {
        "title": "Source inventory",
        "intro": "Generated automatically (`python -m arm_budget docs`) from the tables `meta_year`, `meta_request`, "
                 "`meta_probe`, `meta_document`, `fact_contract` — do not edit by hand.",
        "years": "Years",
        "year_cols": ["year", "SITE_YEAR index", "data as of", "complete year"],
        "requests": "Report requests",
        "request_cols": ["request", "report", "year", "rows", "as of", "fetched (UTC)"],
        "probes": "Probes (code resolution)",
        "probe_cols": ["year", "request", "classifier", "probes", "empty"],
        "contracts": "Contract pages",
        "contract_cols": ["year", "expenditure lines with contracts", "contracts", "file links"],
        "documents": "Documents",
        "document_cols": ["file", "title", "size, KB"],
        "yes": "yes", "no": "no",
    },
    "hy": {
        "title": "Աղբյուրների ցանկ",
        "intro": "Ստեղծվում է ավտոմատ (`python -m arm_budget docs`) `meta_year`, `meta_request`, `meta_probe`, "
                 "`meta_document`, `fact_contract` աղյուսակներից․ ձեռքով մի խմբագրեք։",
        "years": "Տարիներ",
        "year_cols": ["տարի", "SITE_YEAR ինդեքս", "տվյալները առ", "ամբողջական տարի"],
        "requests": "Հաշվետվությունների հարցումներ",
        "request_cols": ["հարցում", "հաշվետվություն", "տարի", "տողեր", "առ", "ներբեռնված (UTC)"],
        "probes": "Ստուգիչ հարցումներ (ծածկագրերի որոշում)",
        "probe_cols": ["տարի", "հարցում", "դասակարգիչ", "հարցումներ", "դատարկ"],
        "contracts": "Պայմանագրերի էջեր",
        "contract_cols": ["տարի", "պայմանագրերով ծախսային տողեր", "պայմանագրեր", "ֆայլերի հղումներ"],
        "documents": "Փաստաթղթեր",
        "document_cols": ["ֆայլ", "անվանում", "չափ, ԿԲ"],
        "yes": "այո", "no": "ոչ",
    },
    "ru": {
        "title": "Перечень источников",
        "intro": "Генерируется автоматически (`python -m arm_budget docs`) из таблиц `meta_year`, `meta_request`, "
                 "`meta_probe`, `meta_document`, `fact_contract` — не редактировать вручную.",
        "years": "Годы",
        "year_cols": ["год", "индекс SITE_YEAR", "данные на", "полный год"],
        "requests": "Запросы отчетов",
        "request_cols": ["запрос", "отчет", "год", "строк", "на дату", "загружено (UTC)"],
        "probes": "Пробные запросы (определение кодов)",
        "probe_cols": ["год", "запрос", "классификатор", "запросов", "пустых"],
        "contracts": "Страницы договоров",
        "contract_cols": ["год", "строк расходов с договорами", "договоров", "ссылок на файлы"],
        "documents": "Документы",
        "document_cols": ["файл", "название", "размер, КБ"],
        "yes": "да", "no": "нет",
    },
}


def _row(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def _table(cols, rows) -> list[str]:
    return [_row(cols), "|" + "---|" * len(cols), *[_row(_md(x) for x in r) for r in rows]]


def write_inventory(con, docs_dir) -> None:
    """docs/<lang>/inventory.md: years, requests, probes, contracts and documents, in each language."""
    years = con.execute("SELECT year, year_index, as_of_date, is_complete FROM meta_year ORDER BY year").fetchall()
    requests = con.execute("""
        SELECT request_id, report, year, n_records, as_of_date, strftime(fetched_at, '%Y-%m-%d %H:%M')
        FROM meta_request ORDER BY year, report, name""").fetchall()
    probes = con.execute("""
        SELECT year, request, dim, count(*), count(*) FILTER (WHERE n_records = 0)
        FROM meta_probe GROUP BY ALL ORDER BY ALL""").fetchall()
    contracts = con.execute("""
        SELECT c.year, count(DISTINCT c.contract_line_id), count(*), sum(c.n_files)
        FROM fact_contract c GROUP BY c.year ORDER BY c.year""").fetchall()
    documents = con.execute("SELECT file, url, title_hy, title_en, title_ru, size_bytes FROM meta_document ORDER BY file").fetchall()
    for lang, tx in INVENTORY_TEXT.items():
        lines = [f"# {tx['title']}", "", tx["intro"], "", f"## {tx['years']}", ""]
        lines += _table(tx["year_cols"], [(y, i, d, tx["yes"] if c else tx["no"]) for y, i, d, c in years])
        lines += ["", f"## {tx['requests']}", ""] + _table(tx["request_cols"], requests)
        lines += ["", f"## {tx['probes']}", ""] + _table(tx["probe_cols"], probes)
        lines += ["", f"## {tx['contracts']}", ""] + _table(tx["contract_cols"], [(y, f"{a:,}", f"{b:,}", f"{c:,}") for y, a, b, c in contracts])
        lines += ["", f"## {tx['documents']}", ""]
        rows = []
        for f, url, hy, en, ru, size in documents:
            title = {"hy": hy, "en": en, "ru": ru}[lang] or hy
            rows.append((f"[{f}]({url})", title, f"{size / 1024:,.0f}"))
        lines += _table(tx["document_cols"], rows)
        out = docs_dir / lang / "inventory.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")


QC_TEXT = {
    "en": {"cols": ["check", "status", "issues", "meaning"], "date": "Collected on {date}; the latest data refer to {as_of}.",
           "status": {"ok": "OK", "warn": "attention", "info": "info"}},
    "hy": {"cols": ["ստուգում", "կարգավիճակ", "խնդիրներ", "նշանակություն"], "date": "Հավաքված է {date}. վերջին տվյալները առ {as_of}։",
           "status": {"ok": "OK", "warn": "ուշադրություն", "info": "տեղեկատվական"}},
    "ru": {"cols": ["проверка", "статус", "проблем", "смысл"], "date": "Собрано {date}; последние данные на {as_of}.",
           "status": {"ok": "OK", "warn": "внимание", "info": "справочно"}},
}
QC_MEANING = {
    "unresolved_code": ("rows of the fact trees without a classifier code", "ծածկագիր չունեցող տողեր փաստերի ծառերում",
                        "строки деревьев фактов без кода классификатора"),
    "tree_total": ("fact rows do not add up to the published grand total", "փաստերի տողերը չեն գումարվում հրապարակված հանրագումարին",
                   "строки фактов не сходятся с опубликованным итогом"),
    "tree_subtotal": ("published subtotals differ from the sum of their children", "հրապարակված միջանկյալ հանրագումարները տարբերվում են ենթատողերի գումարից",
                      "опубликованные промежуточные итоги отличаются от суммы дочерних строк"),
    "revenue_types": ("revenue types do not add up to all revenues", "եկամտի տեսակները չեն գումարվում ընդհանուր եկամուտներին",
                      "виды доходов не сходятся со всеми доходами"),
    "revenue_unallocated": ("year × revenue type with plan not distributed to the accounts", "տարի × եկամտի տեսակ՝ հաշիվներին չբաշխված պլանով",
                            "год × вид дохода с планом, не распределенным по счетам"),
    "site_total": ("start page totals differ from the database", "գլխավոր էջի հանրագումարները տարբերվում են բազայից",
                   "итоги на стартовой странице отличаются от базы"),
    "balance": ("expenditure plan − revenue plan ≠ deficit plan (> 0.1 %)", "ծախսերի պլան − եկամուտների պլան ≠ դեֆիցիտի պլան (> 0,1 %)",
                "план расходов − план доходов ≠ план дефицита (> 0,1 %)"),
    "contract_link": ("contract lines without contract pages / pages without a line", "պայմանագրերով տողեր առանց էջի / էջեր առանց տողի",
                      "строки с договорами без страниц / страницы без строки"),
    "contract_paid": ("lines where payments under contracts exceed the executed amount", "տողեր, որտեղ պայմանագրային վճարումները գերազանցում են կատարումը",
                      "строки, где оплаты по договорам превышают исполнение"),
    "missing_translation": ("names without an English or Russian translation", "առանց անգլերեն կամ ռուսերեն թարգմանության անվանումներ",
                            "названия без английского или русского перевода"),
    "renamed_code": ("codes whose name changed between years", "ծածկագրեր, որոնց անվանումը փոխվել է տարիների միջև",
                     "коды, название которых менялось по годам"),
}
QC_START, QC_END = "<!-- QC_RESULTS -->", "<!-- /QC_RESULTS -->"


def write_qc_results(con, docs_dir) -> None:
    """Replace the block between the QC_RESULTS markers of docs/<lang>/data_quality.md with qc_summary."""
    rows = con.execute("SELECT check_name, status, n_issues FROM qc_summary ORDER BY check_name").fetchall()
    date = con.execute("SELECT max(fetched_at)::DATE FROM meta_request").fetchone()[0]
    as_of = con.execute("SELECT max(as_of_date) FROM meta_year").fetchone()[0]
    for i, (lang, tx) in enumerate(QC_TEXT.items()):
        path = docs_dir / lang / "data_quality.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if QC_START not in text:
            continue
        table = [tx["date"].format(date=date, as_of=as_of), "", _row(tx["cols"]), "|" + "---|" * len(tx["cols"])]
        for name, status, n in rows:
            meaning = QC_MEANING.get(name, ("", "", ""))[("en", "hy", "ru").index(lang)]
            table.append(_row([f"`{name}`", tx["status"].get(status, status), f"{n:,}", meaning]))
        block = QC_START + "\n" + "\n".join(table) + "\n" + QC_END
        start = text.index(QC_START)
        end = text.index(QC_END) + len(QC_END) if QC_END in text else start + len(QC_START)
        path.write_text(text[:start] + block + text[end:], encoding="utf-8")


def write_data_dictionary(db_path=None, out=None) -> None:
    db_path = db_path or config.DUCKDB_PATH
    out = out or (config.ROOT / "docs" / "data_dictionary.md")
    con = duckdb.connect(str(db_path), read_only=True)
    objects = con.execute("""
        SELECT table_name, 'table' AS kind, comment FROM duckdb_tables() WHERE schema_name = 'main'
        UNION ALL
        SELECT view_name, 'view', comment FROM duckdb_views() WHERE schema_name = 'main' AND NOT internal
        ORDER BY 1
    """).fetchall()
    cols = con.execute("""
        SELECT table_name, column_name, data_type, comment, column_index
        FROM duckdb_columns() WHERE schema_name = 'main' ORDER BY table_name, column_index
    """).fetchall()
    by_table: dict[str, list] = {}
    for t, c, typ, com, _ in cols:
        by_table.setdefault(t, []).append((c, typ, com))
    lines = [
        "# Data dictionary",
        "",
        "Generated automatically from the DuckDB catalog by `python -m arm_budget docs` — do not edit by hand.",
        ("The descriptions of tables and columns are also stored in the database itself (`duckdb_tables()`, "
         "`duckdb_columns()`) and are defined in `sql/schema.sql`, `sql/views.sql`, `sql/qc.sql` (`COMMENT ON`). "
         "Schema overview: [database.md](en/database.md) ([hy](hy/database.md), [ru](ru/database.md))."),
        "",
    ]
    for prefix, title in PREFIX_TITLES:
        group = [o for o in objects if o[0].startswith(prefix)]
        if not group:
            continue
        lines += [f"## {title}", ""]
        for name, kind, comment in group:
            rows = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            lines += [f"### `{name}` ({kind}, {rows:,} rows)", "", _md(comment) or "_no description_", "",
                      "| column | type | description |", "|---|---|---|"]
            for c, typ, com in by_table.get(name, []):
                lines.append(f"| `{c}` | {typ} | {_md(com)} |")
            lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_inventory(con, out.parent)
    write_qc_results(con, out.parent)
    con.close()
    log.info("written %s and %s/*/inventory.md", out, out.parent)
