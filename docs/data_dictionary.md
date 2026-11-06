# Data dictionary

Generated automatically from the DuckDB catalog by `python -m arm_budget docs` — do not edit by hand.
The descriptions of tables and columns are also stored in the database itself (`duckdb_tables()`, `duckdb_columns()`) and are defined in `sql/schema.sql`, `sql/views.sql`, `sql/qc.sql` (`COMMENT ON`). Schema overview: [database.md](en/database.md) ([hy](hy/database.md), [ru](ru/database.md)).

## Metadata / provenance

### `meta_document` (table, 3 rows)

PDF documents linked from the forms (guidelines on the application of the budget classification); stored in data/raw/documents.

| column | type | description |
|---|---|---|
| `file` | VARCHAR |  |
| `url` | VARCHAR |  |
| `title_hy` | VARCHAR |  |
| `title_en` | VARCHAR |  |
| `title_ru` | VARCHAR |  |
| `reports` | VARCHAR |  |
| `size_bytes` | BIGINT |  |
| `sha256` | VARCHAR |  |
| `fetched_at` | TIMESTAMP |  |

### `meta_label` (table, 50 rows)

Labels of the source interface (column captions, form fields, options) with translations.

| column | type | description |
|---|---|---|
| `context` | VARCHAR |  |
| `key` | VARCHAR |  |
| `hy` | VARCHAR |  |
| `en` | VARCHAR |  |
| `ru` | VARCHAR |  |

### `meta_language` (table, 3 rows)

Languages of the names in the database: hy is the language of the source, en and ru are translations.

| column | type | description |
|---|---|---|
| `lang` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_native` | VARCHAR |  |

### `meta_probe` (table, 298 rows)

Probes: the query of a request filtered by one classifier code, used to resolve codes of names that are ambiguous or do not match the classifier list (see docs/en/sources.md).

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `request` | VARCHAR | Request name the probe belongs to (expenditure, revenue-t1, ...) |
| `dim` | VARCHAR | Classifier filtered (dimension key) |
| `code` | VARCHAR |  |
| `file` | VARCHAR |  |
| `n_records` | INTEGER | 0 if the filtered query returned nothing |
| `fetched_at` | TIMESTAMP |  |

### `meta_report` (table, 3 rows)

The three reports of the site (left menu "ԲՅՈՒՋԵ"): expenditures, revenues, deficit financing.

| column | type | description |
|---|---|---|
| `report` | VARCHAR |  |
| `page` | VARCHAR | Form page of the site (param.php?page=...) |
| `title_hy` | VARCHAR |  |
| `title_en` | VARCHAR |  |
| `title_ru` | VARCHAR |  |
| `fact_table` | VARCHAR | Table with the facts of the report |

### `meta_request` (table, 24 rows)

Report queries sent to the site (one per report variant and year) and the files with their results.

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR | <name>@<year>, e.g. expenditure@2026, revenue-t1@2025, deficit-v2@2024 |
| `name` | VARCHAR | expenditure (tree of 6 classifiers) \| expenditure-contract-lines (lines with contracts) \| revenue-t<type> \| deficit-v<view> |
| `report` | VARCHAR |  |
| `year` | INTEGER |  |
| `revenue_type` | INTEGER | Revenue type (SITE_EBUDG) of revenue requests: 0 all, 1 taxes and duties, 2 official grants, 3 other revenues |
| `deficit_view` | INTEGER | Deficit view (SITE_DALL): 1 totals only, 2 all lines |
| `params` | VARCHAR | Form fields sent (JSON list of [name, value]) |
| `file` | VARCHAR | Result page under data/ (gzip HTML) |
| `export_file` | VARCHAR | Excel export (SpreadsheetML) of the same result under data/ |
| `export_title` | VARCHAR | Title row of the Excel export |
| `as_of_date` | DATE | Date the data refer to, from the export title |
| `n_records` | INTEGER |  |
| `content_sha256` | VARCHAR | Hash of the grid records (independent of the session id in the HTML) |
| `fetched_at` | TIMESTAMP |  |

### `meta_site_total` (table, 3 rows)

Totals shown in the left menu of the start page (annual plan of the latest year), thousand AMD.

| column | type | description |
|---|---|---|
| `report` | VARCHAR |  |
| `label_hy` | VARCHAR |  |
| `total_kamd` | DECIMAL(18,2) |  |
| `year` | INTEGER |  |
| `fetched_at` | TIMESTAMP |  |

### `meta_year` (table, 3 rows)

Budget years available on the site. The site keeps only the latest three years.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `year_index` | INTEGER | Value of the SITE_YEAR option on the form (1 = the latest year); changes when a new year is added |
| `as_of_date` | DATE | Date the data refer to (title of the Excel export of the expenditure report, "առ dd/mm/yy") |
| `is_complete` | BOOLEAN | TRUE if the data refer to the end of the year (as_of_date in the last days of December) |

## Dimensions (classifiers)

### `dim_department` (table, 75 rows)

Departmental (administrative) classification: state bodies managing the budget appropriations / collecting revenues. 6-digit codes; 3xxxxx «Այլ մարմիններ» are other bodies.

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |
| `in_expenditure` | BOOLEAN | Code appears in the expenditure classifier lists |
| `in_revenue` | BOOLEAN | Code appears in the revenue classifier lists |

### `dim_economic` (table, 83 rows)

Economic classification of expenditures: articles («Հոդված», 4 digits) as published by the site, with their upper levels (dim_economic_level).

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `class_code` | VARCHAR | First digit: 4 current expenditures, 5 expenditures on non-financial assets, 6 receipts from the sale of non-financial assets (negative expenditures), 7 technical articles |
| `category_code` | VARCHAR | First 2 digits (e.g. 41 compensation of employees, 42 purchase of services and goods) |
| `group_code` | VARCHAR | First 3 digits (e.g. 411 wages and salaries in cash) |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `dim_economic_level` (table, 56 rows)

Upper levels of the economic classification (class 1 digit, category 2 digits, group 3 digits). Not published by the site as data: Armenian names from the classification guidelines linked from the forms (meta_document), translations in src/arm_budget/reference.py.

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `level` | INTEGER | 1 class, 2 category, 3 group |
| `level_name` | VARCHAR |  |
| `parent_code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |

### `dim_functional` (table, 167 rows)

Functional classification of expenditures (based on COFOG): section (2 digits, «բաժին») -> group (4 digits, «խումբ») -> class (6 digits, «դաս»).

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `level` | INTEGER | 1 section, 2 group, 3 class |
| `level_name` | VARCHAR | section \| group \| class |
| `parent_code` | VARCHAR | Code of the upper level (first 2 or 4 digits) |
| `name_hy` | VARCHAR | Name in Armenian as in the classifier list of the latest year the code appears (in all dim_* tables: if the list gives the code without a name, the label of the result grid) |
| `name_en` | VARCHAR | English translation (data/translations) |
| `name_ru` | VARCHAR | Russian translation (data/translations) |
| `first_year` | INTEGER | First year the code appears in the classifier lists of the site |
| `last_year` | INTEGER | Last year the code appears in the classifier lists of the site |

### `dim_name` (table, 5,758 rows)

Name of every classifier code in every year, as in the checkbox lists of the forms (names can change between years).

| column | type | description |
|---|---|---|
| `report` | VARCHAR |  |
| `dim` | VARCHAR | func_section \| func_group \| func_class \| program \| department \| economic \| rev_section \| rev_group \| rev_account |
| `code` | VARCHAR |  |
| `year` | INTEGER |  |
| `name_hy` | VARCHAR |  |

### `dim_period` (table, 4 rows)

Periods of the report columns. All plans and executed amounts are cumulative from 1 January.

| column | type | description |
|---|---|---|
| `period` | VARCHAR | q1 (January-March), h1 (January-June), m9 (January-September), year (January-December) |
| `months` | INTEGER |  |
| `sort` | INTEGER |  |
| `label_hy` | VARCHAR |  |
| `label_en` | VARCHAR |  |
| `label_ru` | VARCHAR |  |

### `dim_program` (table, 1,160 rows)

Expenditure programs/measures («Ծրագիր» on the site): 6-digit codes of the treasury system with the name of the budget program measure.

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `dim_revenue_account` (table, 537 rows)

Treasury revenue accounts («Հաշիվ», 12-digit codes 900005xxxxxx): the finest level of the revenue report.

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `dim_revenue_group` (table, 195 rows)

Revenue classification, lower level («Խումբ», 4-digit codes). The codes do not start with the section code.

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `dim_revenue_section` (table, 37 rows)

Revenue classification, upper level («Բաժին» on the revenue form, 2-digit codes: VAT from legal persons, excise tax on imports, ...).

| column | type | description |
|---|---|---|
| `code` | VARCHAR |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |
| `first_year` | INTEGER |  |
| `last_year` | INTEGER |  |

### `dim_revenue_type` (table, 4 rows)

Types of revenue («ԵԿԱՄՈՒՏՆԵՐԻ ՏԵՍԱԿՆԵՐ», form field SITE_EBUDG). 0 = all revenues is used only for checks.

| column | type | description |
|---|---|---|
| `revenue_type` | INTEGER |  |
| `name_hy` | VARCHAR |  |
| `name_en` | VARCHAR |  |
| `name_ru` | VARCHAR |  |

### `dim_translation` (table, 2,239 rows)

Translation dictionary Armenian -> English / Russian (data/translations/<context>.csv). Machine-assisted translation, reviewed for consistency; the Armenian text is authoritative.

| column | type | description |
|---|---|---|
| `context` | VARCHAR | File the translation comes from: functional, program, department, economic, revenue, deficit, labels, ... |
| `hy` | VARCHAR |  |
| `en` | VARCHAR |  |
| `ru` | VARCHAR |  |

## Facts

### `fact_contract` (table, 75,795 rows)

Contracts financed from an expenditure line (popup «Պայմանագրի դիտում» of the site). A contract financed from several lines appears once per line.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `contract_line_id` | INTEGER | Expenditure line (fact_expenditure.contract_line_id) |
| `seq` | INTEGER | Order of the contract on the page |
| `partner_hy` | VARCHAR | Counterparty as published («Գործընկեր») |
| `partner_en` | VARCHAR | Counterparty transliterated to Latin script, legal form abbreviation translated (automatic) |
| `partner_ru` | VARCHAR | Counterparty transliterated to Cyrillic, legal form abbreviation translated (automatic) |
| `start_date` | DATE |  |
| `end_date` | DATE |  |
| `amount_kamd` | DECIMAL(18,2) | Contract amount («Պայմ.գումարը»), thousand AMD |
| `paid_kamd` | DECIMAL(18,2) | Paid from this expenditure line («Վճարված գումար»), thousand AMD |
| `n_files` | INTEGER |  |

### `fact_contract_file` (table, 279,252 rows)

Links to the documents of a contract: the contract in the e-procurement system (armeps.am) and scans stored on the site (xml/storage/*.pdf). Files are not downloaded.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `contract_line_id` | INTEGER |  |
| `seq` | INTEGER |  |
| `file_no` | INTEGER |  |
| `url` | VARCHAR |  |
| `host` | VARCHAR |  |
| `link_text` | VARCHAR |  |

### `fact_deficit` (table, 256 rows)

Sources of financing of the budget deficit, all lines of the report (SITE_DALL = 2), in the order of the source. The report is a formatted statement, not a classifier: only numbered lines add up (see row_kind).

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `line_no` | INTEGER |  |
| `label_hy` | VARCHAR | Line label as published (leading spaces removed, see indent) |
| `label_en` | VARCHAR | English translation of the label (data/translations/deficit.csv) |
| `label_ru` | VARCHAR | Russian translation of the label (data/translations/deficit.csv) |
| `item_code` | VARCHAR | Position derived from the numbering: TOTAL, A / B (domestic / external sources), A.1, A.1.1, ...; NULL for detail lines |
| `row_kind` | VARCHAR | total \| source (A, B) \| item (1., 2.) \| subitem (1.1) \| detail (unnumbered breakdown of the preceding numbered line: bodies, companies, loans) \| note (separator rows «այդ թվում» including, «որից» of which; no values) |
| `level` | INTEGER | 0 total, 1 source, 2 item, 3 subitem, 4 detail |
| `parent_line_no` | INTEGER | line_no of the numbered line this line belongs to |
| `note_hy` | VARCHAR | Separator above the detail line: «այդ թվում» (including) or «որից» (of which) |
| `indent` | INTEGER | Number of leading spaces of the label (nesting of detail lines in the source) |
| `in_totals_view` | BOOLEAN | TRUE if the line is also shown in the totals view (SITE_DALL = 1) |
| `is_highlighted` | BOOLEAN | TRUE if the source highlights the row (numbered lines) |
| `q1_plan_kamd` | DECIMAL(18,2) |  |
| `q1_actual_kamd` | DECIMAL(18,2) |  |
| `h1_plan_kamd` | DECIMAL(18,2) |  |
| `h1_actual_kamd` | DECIMAL(18,2) |  |
| `m9_plan_kamd` | DECIMAL(18,2) |  |
| `m9_actual_kamd` | DECIMAL(18,2) |  |
| `year_plan_kamd` | DECIMAL(18,2) |  |
| `year_actual_kamd` | DECIMAL(18,2) | Since 1 January up to meta_year.as_of_date, thousand AMD |
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |

### `fact_expenditure` (table, 10,986 rows)

State budget expenditures at the finest level published: functional class x program/measure x department x economic article. Thousand AMD; plans and executed amounts cumulative from 1 January.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `line_no` | INTEGER | Number of the line within the year (order of the source tree, sorted by codes) |
| `func_section_code` | VARCHAR | Functional section, 2 digits (dim_functional) |
| `func_group_code` | VARCHAR | Functional group, 4 digits (dim_functional) |
| `func_class_code` | VARCHAR | Functional class, 6 digits (dim_functional) |
| `program_code` | VARCHAR | Program/measure, 6 digits (dim_program) |
| `department_code` | VARCHAR | Department, 6 digits (dim_department) |
| `economic_code` | VARCHAR | Economic article, 4 digits (dim_economic) |
| `contract_line_id` | INTEGER | Id of the line in the contract registry of the site (opens the contracts in fact_contract); NULL if the line has no contracts |
| `q1_plan_kamd` | DECIMAL(18,4) | Plan for January-March, thousand AMD |
| `q1_actual_kamd` | DECIMAL(18,4) | Executed in January-March, thousand AMD |
| `h1_plan_kamd` | DECIMAL(18,4) | Plan for January-June, thousand AMD |
| `h1_actual_kamd` | DECIMAL(18,4) | Executed in January-June, thousand AMD |
| `m9_plan_kamd` | DECIMAL(18,4) | Plan for January-September, thousand AMD |
| `m9_actual_kamd` | DECIMAL(18,4) | Executed in January-September, thousand AMD |
| `year_plan_kamd` | DECIMAL(18,4) | Annual plan, thousand AMD |
| `year_actual_kamd` | DECIMAL(18,4) | Executed since 1 January up to meta_year.as_of_date (the whole year for completed years), thousand AMD |
| `request_id` | VARCHAR | Source request (meta_request) |
| `recid` | INTEGER | Row of the source grid (raw_grid_cell.recid) |

### `fact_revenue` (table, 1,401 rows)

State budget revenues at the finest level published: revenue type x section x group x department x treasury account. Thousand AMD; cumulative from 1 January. Most of the plan is set for the revenue type as a whole: it is in the row line_kind = unallocated; plans of the accounts are partial.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `revenue_type` | INTEGER | 1 taxes and duties, 2 official grants, 3 other revenues (dim_revenue_type) |
| `line_no` | INTEGER |  |
| `line_kind` | VARCHAR | line (an account of the source) \| unallocated (the part of the total plan of the revenue type that is not distributed to the accounts; no codes, one row per year and type) |
| `rev_section_code` | VARCHAR | Revenue section, 2 digits (dim_revenue_section) |
| `rev_group_code` | VARCHAR | Revenue group, 4 digits (dim_revenue_group) |
| `department_code` | VARCHAR | Department administering the revenue (dim_department) |
| `rev_account_code` | VARCHAR | Treasury account, 12 digits (dim_revenue_account) |
| `q1_plan_kamd` | DECIMAL(18,4) |  |
| `q1_actual_kamd` | DECIMAL(18,4) |  |
| `h1_plan_kamd` | DECIMAL(18,4) |  |
| `h1_actual_kamd` | DECIMAL(18,4) |  |
| `m9_plan_kamd` | DECIMAL(18,4) |  |
| `m9_actual_kamd` | DECIMAL(18,4) |  |
| `year_plan_kamd` | DECIMAL(18,4) |  |
| `year_actual_kamd` | DECIMAL(18,4) | Received since 1 January up to meta_year.as_of_date, thousand AMD |
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |

## Staging (report trees)

### `stg_report_node` (table, 24,188 rows)

Every row of the expenditure and revenue trees (grand total, subtotals of every level, leaves) with the resolved code.

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |
| `year` | INTEGER |  |
| `level` | INTEGER | -1 grand total, 0 .. n-1 classifier levels in the order of the grouping |
| `dim` | VARCHAR | Classifier of the level |
| `label_hy` | VARCHAR | Label as in the grid (punctuation removed by the site) |
| `parent_recid` | INTEGER |  |
| `code` | VARCHAR |  |
| `code_method` | VARCHAR | name (unique match with the classifier list of the year) \| name_other_year (unique match with the list of another year) \| probe (filtered query) \| NULL (unresolved) |
| `is_leaf` | BOOLEAN |  |
| `q1_plan_kamd` | DECIMAL(18,4) |  |
| `q1_actual_kamd` | DECIMAL(18,4) |  |
| `h1_plan_kamd` | DECIMAL(18,4) |  |
| `h1_actual_kamd` | DECIMAL(18,4) |  |
| `m9_plan_kamd` | DECIMAL(18,4) |  |
| `m9_actual_kamd` | DECIMAL(18,4) |  |
| `year_plan_kamd` | DECIMAL(18,4) |  |
| `year_actual_kamd` | DECIMAL(18,4) |  |

## Raw cells

### `raw_grid_cell` (table, 416,574 rows)

Lossless copy of every non-empty cell of every report grid (all requests in meta_request), values as strings exactly as in the source.

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |
| `field` | VARCHAR | w2ui field name: c2 ... c20 |
| `caption` | VARCHAR | Column caption of the field |
| `value` | VARCHAR |  |

### `raw_grid_row` (table, 30,982 rows)

Rows of the report grids with the row style of the source (highlighted rows).

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |
| `style` | VARCHAR |  |

## Data quality

### `qc_balance` (table, 2 rows)

Years where the annual expenditure plan minus the revenue plan differs from the planned deficit by more than 0.1 % (informative: the deficit statement can show another edition of the plan).

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `plan_gap_kamd` | DECIMAL(38,4) |  |
| `deficit_plan_kamd` | DECIMAL(18,2) |  |
| `actual_gap_kamd` | DECIMAL(38,4) |  |
| `deficit_actual_kamd` | DECIMAL(18,2) |  |

### `qc_contract_link` (table, 0 rows)

Expenditure lines marked as having contracts without contract data, and contract pages not linked to an expenditure line.

| column | type | description |
|---|---|---|
| `issue` | VARCHAR |  |
| `year` | INTEGER |  |
| `contract_line_id` | INTEGER |  |

### `qc_contract_paid` (table, 53 rows)

Expenditure lines where the payments listed for contracts exceed the executed amount of the line (by more than 1 thousand AMD).

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `contract_line_id` | INTEGER |  |
| `year_actual_kamd` | DECIMAL(18,4) |  |
| `paid_kamd` | DECIMAL(38,2) |  |

### `qc_missing_translation` (table, 0 rows)

Armenian names without an English or Russian translation (python -m arm_budget translations writes them to data/translations/pending).

| column | type | description |
|---|---|---|
| `context` | VARCHAR |  |
| `hy` | VARCHAR |  |

### `qc_renamed_code` (table, 20 rows)

Classifier codes whose name changed between years (informative; dim_* keep the latest name, dim_name all of them).

| column | type | description |
|---|---|---|
| `report` | VARCHAR |  |
| `dim` | VARCHAR |  |
| `code` | VARCHAR |  |
| `n_names` | BIGINT |  |
| `years` | VARCHAR |  |

### `qc_revenue_types` (table, 0 rows)

Years where taxes + grants + other revenues differ from all revenues (SITE_EBUDG 1+2+3 vs 0); plan tolerance 0.01 %.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `types_plan` | DECIMAL(38,4) |  |
| `all_plan` | DECIMAL(18,4) |  |
| `types_actual` | DECIMAL(38,4) |  |
| `all_actual` | DECIMAL(18,4) |  |

### `qc_revenue_unallocated` (table, 6 rows)

Part of the annual revenue plan set for the revenue type as a whole (fact_revenue.line_kind = unallocated).

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `revenue_type` | INTEGER |  |
| `unallocated_plan_kamd` | DECIMAL(38,4) |  |
| `total_plan_kamd` | DECIMAL(38,4) |  |
| `unallocated_pct` | DOUBLE |  |

### `qc_site_total` (table, 0 rows)

Reports whose total on the start page differs from the annual plan in the database.

| column | type | description |
|---|---|---|
| `report` | VARCHAR |  |
| `year` | INTEGER |  |
| `total_kamd` | DECIMAL(18,2) |  |
| `database_kamd` | DECIMAL(38,4) |  |

### `qc_summary` (table, 11 rows)

Summary of the data quality checks (qc_* tables).

| column | type | description |
|---|---|---|
| `check_name` | VARCHAR |  |
| `status` | VARCHAR |  |
| `n_issues` | BIGINT |  |
| `description` | VARCHAR |  |

### `qc_tree_subtotal` (table, 0 rows)

Subtotal rows that differ from the sum of their children.

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |
| `level` | INTEGER |  |
| `label_hy` | VARCHAR |  |
| `year_plan_kamd` | DECIMAL(18,4) |  |
| `children_plan` | DECIMAL(38,4) |  |
| `year_actual_kamd` | DECIMAL(18,4) |  |
| `children_actual` | DECIMAL(38,4) |  |

### `qc_tree_total` (table, 0 rows)

Requests whose fact rows do not add up to the grand total of the source (annual plan or execution, tolerance 1 thousand AMD).

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `facts_plan` | DECIMAL(38,4) |  |
| `total_plan` | DECIMAL(18,4) |  |
| `facts_actual` | DECIMAL(38,4) |  |
| `total_actual` | DECIMAL(18,4) |  |

### `qc_unresolved_code` (table, 0 rows)

Tree nodes of the fact requests whose classifier code could not be resolved (neither by name nor by a probe).

| column | type | description |
|---|---|---|
| `request_id` | VARCHAR |  |
| `recid` | INTEGER |  |
| `year` | INTEGER |  |
| `level` | INTEGER |  |
| `dim` | VARCHAR |  |
| `label_hy` | VARCHAR |  |

## Views

### `v_contract` (view, 75,795 rows)

Contracts with the classification of the expenditure line they are paid from.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `contract_line_id` | INTEGER |  |
| `seq` | INTEGER |  |
| `partner_hy` | VARCHAR |  |
| `partner_en` | VARCHAR |  |
| `partner_ru` | VARCHAR |  |
| `start_date` | DATE |  |
| `end_date` | DATE |  |
| `amount_kamd` | DECIMAL(18,2) |  |
| `paid_kamd` | DECIMAL(18,2) |  |
| `n_files` | INTEGER |  |
| `department_code` | VARCHAR |  |
| `department_en` | VARCHAR |  |
| `program_code` | VARCHAR |  |
| `program_en` | VARCHAR |  |
| `economic_code` | VARCHAR |  |
| `economic_en` | VARCHAR |  |
| `func_class_code` | VARCHAR |  |
| `line_year_plan_kamd` | DECIMAL(18,4) |  |
| `line_year_actual_kamd` | DECIMAL(18,4) |  |

### `v_deficit` (view, 212 rows)

Deficit financing lines without the separator rows. Sum only lines of one row_kind under one parent; detail lines are breakdowns.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `line_no` | INTEGER |  |
| `item_code` | VARCHAR |  |
| `row_kind` | VARCHAR |  |
| `level` | INTEGER |  |
| `parent_line_no` | INTEGER |  |
| `label_hy` | VARCHAR |  |
| `label_en` | VARCHAR |  |
| `label_ru` | VARCHAR |  |
| `note_hy` | VARCHAR |  |
| `in_totals_view` | BOOLEAN |  |
| `q1_plan_kamd` | DECIMAL(18,2) |  |
| `q1_actual_kamd` | DECIMAL(18,2) |  |
| `h1_plan_kamd` | DECIMAL(18,2) |  |
| `h1_actual_kamd` | DECIMAL(18,2) |  |
| `m9_plan_kamd` | DECIMAL(18,2) |  |
| `m9_actual_kamd` | DECIMAL(18,2) |  |
| `year_plan_kamd` | DECIMAL(18,2) |  |
| `year_actual_kamd` | DECIMAL(18,2) |  |

### `v_expenditure` (view, 10,986 rows)

fact_expenditure with the names of all classifiers in hy / en / ru and the upper levels of the economic classification. Thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `line_no` | INTEGER |  |
| `func_section_code` | VARCHAR |  |
| `func_section_hy` | VARCHAR |  |
| `func_section_en` | VARCHAR |  |
| `func_section_ru` | VARCHAR |  |
| `func_group_code` | VARCHAR |  |
| `func_group_hy` | VARCHAR |  |
| `func_group_en` | VARCHAR |  |
| `func_group_ru` | VARCHAR |  |
| `func_class_code` | VARCHAR |  |
| `func_class_hy` | VARCHAR |  |
| `func_class_en` | VARCHAR |  |
| `func_class_ru` | VARCHAR |  |
| `program_code` | VARCHAR |  |
| `program_hy` | VARCHAR |  |
| `program_en` | VARCHAR |  |
| `program_ru` | VARCHAR |  |
| `department_code` | VARCHAR |  |
| `department_hy` | VARCHAR |  |
| `department_en` | VARCHAR |  |
| `department_ru` | VARCHAR |  |
| `economic_class_code` | VARCHAR |  |
| `economic_class_en` | VARCHAR |  |
| `economic_category_code` | VARCHAR |  |
| `economic_category_en` | VARCHAR |  |
| `economic_group_code` | VARCHAR |  |
| `economic_group_en` | VARCHAR |  |
| `economic_code` | VARCHAR |  |
| `economic_hy` | VARCHAR |  |
| `economic_en` | VARCHAR |  |
| `economic_ru` | VARCHAR |  |
| `contract_line_id` | INTEGER |  |
| `q1_plan_kamd` | DECIMAL(18,4) |  |
| `q1_actual_kamd` | DECIMAL(18,4) |  |
| `h1_plan_kamd` | DECIMAL(18,4) |  |
| `h1_actual_kamd` | DECIMAL(18,4) |  |
| `m9_plan_kamd` | DECIMAL(18,4) |  |
| `m9_actual_kamd` | DECIMAL(18,4) |  |
| `year_plan_kamd` | DECIMAL(18,4) |  |
| `year_actual_kamd` | DECIMAL(18,4) |  |
| `year_execution_pct` | DOUBLE |  |

### `v_expenditure_by_department` (view, 194 rows)

Annual plan and execution of expenditures by department and year, thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `department_code` | VARCHAR |  |
| `department_hy` | VARCHAR |  |
| `department_en` | VARCHAR |  |
| `department_ru` | VARCHAR |  |
| `year_plan_kamd` | DECIMAL(38,4) |  |
| `year_actual_kamd` | DECIMAL(38,4) |  |
| `year_execution_pct` | DOUBLE |  |

### `v_expenditure_by_function` (view, 33 rows)

Annual plan and execution of expenditures by functional section and year, thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `func_section_code` | VARCHAR |  |
| `func_section_hy` | VARCHAR |  |
| `func_section_en` | VARCHAR |  |
| `func_section_ru` | VARCHAR |  |
| `year_plan_kamd` | DECIMAL(38,4) |  |
| `year_actual_kamd` | DECIMAL(38,4) |  |
| `year_execution_pct` | DOUBLE |  |

### `v_expenditure_long` (view, 43,944 rows)

fact_expenditure with one row per period (q1, h1, m9, year): cumulative plan and executed amount, thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `line_no` | INTEGER |  |
| `func_class_code` | VARCHAR |  |
| `program_code` | VARCHAR |  |
| `department_code` | VARCHAR |  |
| `economic_code` | VARCHAR |  |
| `period` | VARCHAR |  |
| `months` | INTEGER |  |
| `plan_kamd` | DECIMAL(18,4) |  |
| `actual_kamd` | DECIMAL(18,4) |  |

### `v_revenue` (view, 1,401 rows)

fact_revenue with the names of all classifiers in hy / en / ru. Thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `revenue_type` | INTEGER |  |
| `revenue_type_hy` | VARCHAR |  |
| `revenue_type_en` | VARCHAR |  |
| `revenue_type_ru` | VARCHAR |  |
| `line_no` | INTEGER |  |
| `line_kind` | VARCHAR |  |
| `rev_section_code` | VARCHAR |  |
| `rev_section_hy` | VARCHAR |  |
| `rev_section_en` | VARCHAR |  |
| `rev_section_ru` | VARCHAR |  |
| `rev_group_code` | VARCHAR |  |
| `rev_group_hy` | VARCHAR |  |
| `rev_group_en` | VARCHAR |  |
| `rev_group_ru` | VARCHAR |  |
| `department_code` | VARCHAR |  |
| `department_hy` | VARCHAR |  |
| `department_en` | VARCHAR |  |
| `department_ru` | VARCHAR |  |
| `rev_account_code` | VARCHAR |  |
| `rev_account_hy` | VARCHAR |  |
| `rev_account_en` | VARCHAR |  |
| `rev_account_ru` | VARCHAR |  |
| `q1_plan_kamd` | DECIMAL(18,4) |  |
| `q1_actual_kamd` | DECIMAL(18,4) |  |
| `h1_plan_kamd` | DECIMAL(18,4) |  |
| `h1_actual_kamd` | DECIMAL(18,4) |  |
| `m9_plan_kamd` | DECIMAL(18,4) |  |
| `m9_actual_kamd` | DECIMAL(18,4) |  |
| `year_plan_kamd` | DECIMAL(18,4) |  |
| `year_actual_kamd` | DECIMAL(18,4) |  |

### `v_revenue_long` (view, 5,604 rows)

fact_revenue with one row per period (q1, h1, m9, year), thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `revenue_type` | INTEGER |  |
| `line_no` | INTEGER |  |
| `line_kind` | VARCHAR |  |
| `rev_section_code` | VARCHAR |  |
| `rev_group_code` | VARCHAR |  |
| `department_code` | VARCHAR |  |
| `rev_account_code` | VARCHAR |  |
| `period` | VARCHAR |  |
| `months` | INTEGER |  |
| `plan_kamd` | DECIMAL(18,4) |  |
| `actual_kamd` | DECIMAL(18,4) |  |

### `v_summary` (view, 3 rows)

Totals by year: annual plan and execution of expenditures, revenues and the deficit, thousand AMD.

| column | type | description |
|---|---|---|
| `year` | INTEGER |  |
| `as_of_date` | DATE |  |
| `is_complete` | BOOLEAN |  |
| `expenditure_plan_kamd` | DECIMAL(38,4) |  |
| `expenditure_actual_kamd` | DECIMAL(38,4) |  |
| `revenue_plan_kamd` | DECIMAL(38,4) |  |
| `revenue_actual_kamd` | DECIMAL(38,4) |  |
| `deficit_plan_kamd` | DECIMAL(18,2) |  |
| `deficit_actual_kamd` | DECIMAL(18,2) |  |
| `expenditure_lines` | BIGINT |  |
| `revenue_lines` | BIGINT |  |
| `contracts` | BIGINT |  |

