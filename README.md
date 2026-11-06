# Armenian state budget: Ministry of Finance data in DuckDB

**English** | [Հայերեն](README.hy.md) | [Русский](README.ru.md)

Collection, normalisation and documentation of the data on the plan and execution of the **state budget of the
Republic of Armenia** published by the Ministry of Finance in the "Interactive budget" («Ինտերակտիվ բյուջե»):
<https://budget.minfin.am:82/>.

The site has only an Armenian interface and shows the data only through queries to its database. The pipeline
collects **everything** the site publishes for all available years (the latest three: 2024–2026):

* **expenditures** at the finest level the site allows: functional classification (section → group → class) ×
  program/measure × department × economic article, ≈3 600 budget lines a year;
* **revenues** by type (taxes and duties / official grants / other) × section × group × department × treasury
  account, ≈450–480 lines a year;
* **deficit** financing (domestic and external sources, all lines of the statement);
* **contracts** paid from every expenditure line (≈2 000 lines a year): counterparty, dates, contract amount,
  amount paid, links to the contract documents;
* the **classifiers with their codes** for every year, the PDF guidelines on the budget classification;

for each line: plan and execution for Q1, January–June, January–September and the year (thousand AMD).

The result is the DuckDB database `data/arm_budget.duckdb` with codes in the fact tables, **names of all
classifiers in Armenian, English and Russian**, a lossless copy of all source cells, data quality checks and
documentation in three languages.

## Ready-made data: releases

The database and the raw data are not stored in git. Each collection run is published as a repository **release**
([Releases](https://github.com/opendataam/arm-budget/releases)) tagged `data-YYYY-MM-DD` — the collection date;
the tag points to the code commit the database was built with.

| release asset | contents |
|---|---|
| `arm_budget.duckdb.xz` | DuckDB database |
| `arm_budget-parquet.zip` | all tables and views as Parquet + data dictionary |
| `arm_budget-raw.tar.xz` | raw data: report pages, Excel exports, probes, contract pages, PDF (`raw/`) and manifests (`catalog/`) |
| `SHA256SUMS` | checksums |

```bash
make install
make download            # latest release: database -> data/arm_budget.duckdb (SHA256 verified)
make lab                 # notebook with examples
```

Other options: `make download-parquet`, `make download-raw` (then `make build` rebuilds the database without
touching the website), a specific snapshot — `make download TAG=data-2026-11-05`. Without Python:
`curl -LO https://github.com/opendataam/arm-budget/releases/latest/download/arm_budget.duckdb.xz && xz -d arm_budget.duckdb.xz`.

**The site keeps only the latest three years**: the releases are also an archive of the years that disappear from it.

## Quick start: build everything yourself

```bash
make install   # creates .venv and installs the package with the dev + notebook extras (via uv if available; Python ≥ 3.10)
make all       # catalog → fetch → contracts → build → docs  (≈4–6 hours, mostly waiting for the site)
```

Or step by step (in the activated environment: `source .venv/bin/activate`):

```bash
python -m arm_budget catalog     # start page, forms of every report for every year (classifiers with codes), PDFs -> data/catalog
python -m arm_budget fetch       # report queries, Excel exports, code probes -> data/raw/reports, data/raw/probes
python -m arm_budget contracts   # contract pages of the expenditure lines -> data/raw/contracts
python -m arm_budget build       # -> data/arm_budget.duckdb
python -m arm_budget docs        # -> docs/data_dictionary.md, docs/{en,hy,ru}/inventory.md
```

Example query:

```bash
duckdb -readonly data/arm_budget.duckdb -c "
  SELECT year, func_section_en, round(year_actual_kamd / 1e6, 1) AS executed_bn_amd
  FROM v_expenditure_by_function ORDER BY year, func_section_code"
```

## Jupyter notebook with examples

[`docs/examples.ipynb`](docs/examples.ipynb): example queries and charts (the text of the notebook is in Russian;
stored with outputs, readable on GitHub).
`make lab` opens it in JupyterLab (settings in [`scripts/jupyter_lab_config.py`](scripts/jupyter_lab_config.py)),
`make notebook` re-executes it and saves the outputs. The first cell finds the repository root and opens the
database read-only. After `make build`, restart the kernel.

## Repository layout

```
├── README.md                  this file (English); README.hy.md — Armenian, README.ru.md — Russian
├── Makefile                   pipeline commands
├── pyproject.toml             arm_budget package (CLI: arm-budget)
├── src/arm_budget/
│   ├── config.py              paths, URL, HTTP settings, reports and classifiers of the site
│   ├── site.py                client of the site: session, forms, queries, results, exports, contracts
│   ├── fetch.py               steps catalog / fetch / contracts, manifests in data/catalog
│   ├── tree.py                grouped result grid -> tree of nodes
│   ├── resolve.py             classifier codes by name and by probes
│   ├── build.py               DuckDB build
│   ├── translations.py        hy -> en / ru dictionaries (data/translations)
│   ├── translit.py            transliteration of counterparty names
│   ├── reference.py           static trilingual reference data
│   ├── docs.py, release.py    generated documentation; data snapshots in GitHub releases
│   ├── cli.py, __main__.py    command line
│   └── parsers/               grid, forms, contracts, deficit statement, Excel export, value cleaning
├── sql/
│   ├── schema.sql             tables + COMMENT ON (descriptions are stored in the database itself)
│   ├── views.sql              views
│   └── qc.sql                 data quality checks
├── data/
│   ├── catalog/               manifests (in git): site.json, classifiers/, requests.json, probes.json, contracts/, documents.json
│   ├── translations/          translation dictionaries hy -> en / ru (in git) and GLOSSARY.md
│   ├── raw/                   downloaded pages, exports, probes, contracts, PDFs (not in git; in releases)
│   └── arm_budget.duckdb      result (not in git; in releases)
├── docs/
│   ├── en/, hy/, ru/          documentation in English, Armenian and Russian
│   ├── data_dictionary.md     all tables and columns (generated)
│   └── examples.ipynb         Jupyter notebook with examples
├── scripts/                   notebook runner and JupyterLab settings
└── tests/                     tests of the parsers, code resolution, documentation and the built database
```

## Documentation

The documentation is available in English ([docs/en](docs/en)), Armenian ([docs/hy](docs/hy)) and Russian
([docs/ru](docs/ru)).

| document | contents |
|---|---|
| [sources.md](docs/en/sources.md) | the site, its reports, how its query interface works, quirks, units, codes and probes |
| [database.md](docs/en/database.md) | database design: principles, schema (ER), tables, views, example queries |
| [data_dictionary.md](docs/data_dictionary.md) | all tables and columns (generated) |
| [translations.md](docs/en/translations.md) | names in three languages: dictionaries, method, how to translate new names |
| [data_quality.md](docs/en/data_quality.md) | data quality checks and known issues of the source |
| [inventory.md](docs/en/inventory.md) | years, requests, probes, contracts, documents (generated) |
| [maintenance.md](docs/en/maintenance.md) | updates, a new budget year, changes on the site, code layout |
| [examples.ipynb](docs/examples.ipynb) | Jupyter notebook: example queries and charts |

## Main tables

| table / view | contents |
|---|---|
| `v_expenditure` / `fact_expenditure` | expenditures: functional class × program × department × economic article, plan and execution by period |
| `v_revenue` / `fact_revenue` | revenues: type × section × group × department × treasury account |
| `v_deficit` / `fact_deficit` | sources of deficit financing |
| `v_contract` / `fact_contract`, `fact_contract_file` | contracts of the expenditure lines and links to their documents |
| `v_summary`, `v_expenditure_by_function`, `v_expenditure_by_department` | totals |
| `dim_functional`, `dim_program`, `dim_department`, `dim_economic`, `dim_revenue_*` | classifiers with names in hy / en / ru |
| `stg_report_node`, `raw_grid_cell` | all rows of the report trees (incl. subtotals) and all source cells |

## Caveats

* Amounts are in thousand AMD, cumulative from 1 January; the latest year is incomplete (`meta_year.as_of_date`).
* Revenue plans are set mostly for the revenue type as a whole (`fact_revenue.line_kind = 'unallocated'`); compare
  plans and execution of revenues at the level of the type.
* Only numbered lines of the deficit statement add up (`item_code IS NOT NULL`).
* English and Russian names are machine-assisted translations; the Armenian names are authoritative.

## Source

Data: Ministry of Finance of the Republic of Armenia, <https://budget.minfin.am:82/>. A licence for the repository
code has not been chosen yet.
