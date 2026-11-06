-- DuckDB schema of the Armenian state budget execution database
-- (source: "Interactive budget" of the Ministry of Finance, https://budget.minfin.am:82/).
-- Table prefixes:
--   meta_  provenance: site, years, requests, probes, documents, labels of the source
--   dim_   reference dimensions (classifiers) with names in hy / en / ru
--   fact_  facts: expenditures, revenues, deficit financing, contracts
--   stg_   every node of every report tree (subtotals included) with resolved codes
--   raw_   lossless copy of every cell of every report grid
--   qc_    data quality checks (created by the build, sql/qc.sql)
--   v_     views (sql/views.sql)
-- Amounts are in thousand Armenian drams (suffix _kamd), as published.
-- Comments on every table and column are stored in the database catalog
-- (duckdb_tables() / duckdb_columns()) and rendered into docs/data_dictionary.md.

------------------------------------------------------------------------------
-- metadata / provenance
------------------------------------------------------------------------------
CREATE TABLE meta_language (
    lang        VARCHAR PRIMARY KEY,
    name_en     VARCHAR,
    name_native VARCHAR
);
COMMENT ON TABLE meta_language IS 'Languages of the names in the database: hy is the language of the source, en and ru are translations.';

CREATE TABLE meta_report (
    report    VARCHAR PRIMARY KEY,
    page      VARCHAR,
    title_hy  VARCHAR,
    title_en  VARCHAR,
    title_ru  VARCHAR,
    fact_table VARCHAR
);
COMMENT ON TABLE meta_report IS 'The three reports of the site (left menu "ԲՅՈՒՋԵ"): expenditures, revenues, deficit financing.';
COMMENT ON COLUMN meta_report.page IS 'Form page of the site (param.php?page=...)';
COMMENT ON COLUMN meta_report.fact_table IS 'Table with the facts of the report';

CREATE TABLE meta_year (
    year         INTEGER PRIMARY KEY,
    year_index   INTEGER,
    as_of_date   DATE,
    is_complete  BOOLEAN
);
COMMENT ON TABLE meta_year IS 'Budget years available on the site. The site keeps only the latest three years.';
COMMENT ON COLUMN meta_year.year_index IS 'Value of the SITE_YEAR option on the form (1 = the latest year); changes when a new year is added';
COMMENT ON COLUMN meta_year.as_of_date IS 'Date the data refer to (title of the Excel export of the expenditure report, "առ dd/mm/yy")';
COMMENT ON COLUMN meta_year.is_complete IS 'TRUE if the data refer to the end of the year (as_of_date in the last days of December)';

CREATE TABLE meta_site_total (
    report      VARCHAR PRIMARY KEY,
    label_hy    VARCHAR,
    total_kamd  DECIMAL(18, 2),
    year        INTEGER,
    fetched_at  TIMESTAMP
);
COMMENT ON TABLE meta_site_total IS 'Totals shown in the left menu of the start page (annual plan of the latest year), thousand AMD.';

CREATE TABLE meta_request (
    request_id      VARCHAR PRIMARY KEY,
    name            VARCHAR NOT NULL,
    report          VARCHAR NOT NULL,
    year            INTEGER NOT NULL,
    revenue_type    INTEGER,
    deficit_view    INTEGER,
    params          VARCHAR,
    file            VARCHAR,
    export_file     VARCHAR,
    export_title    VARCHAR,
    as_of_date      DATE,
    n_records       INTEGER,
    content_sha256  VARCHAR,
    fetched_at      TIMESTAMP
);
COMMENT ON TABLE meta_request IS 'Report queries sent to the site (one per report variant and year) and the files with their results.';
COMMENT ON COLUMN meta_request.request_id IS '<name>@<year>, e.g. expenditure@2026, revenue-t1@2025, deficit-v2@2024';
COMMENT ON COLUMN meta_request.name IS 'expenditure (tree of 6 classifiers) | expenditure-contract-lines (lines with contracts) | revenue-t<type> | deficit-v<view>';
COMMENT ON COLUMN meta_request.revenue_type IS 'Revenue type (SITE_EBUDG) of revenue requests: 0 all, 1 taxes and duties, 2 official grants, 3 other revenues';
COMMENT ON COLUMN meta_request.deficit_view IS 'Deficit view (SITE_DALL): 1 totals only, 2 all lines';
COMMENT ON COLUMN meta_request.params IS 'Form fields sent (JSON list of [name, value])';
COMMENT ON COLUMN meta_request.file IS 'Result page under data/ (gzip HTML)';
COMMENT ON COLUMN meta_request.export_file IS 'Excel export (SpreadsheetML) of the same result under data/';
COMMENT ON COLUMN meta_request.export_title IS 'Title row of the Excel export';
COMMENT ON COLUMN meta_request.as_of_date IS 'Date the data refer to, from the export title';
COMMENT ON COLUMN meta_request.content_sha256 IS 'Hash of the grid records (independent of the session id in the HTML)';

CREATE TABLE meta_probe (
    year        INTEGER NOT NULL,
    request     VARCHAR NOT NULL,
    dim         VARCHAR NOT NULL,
    code        VARCHAR NOT NULL,
    file        VARCHAR,
    n_records   INTEGER,
    fetched_at  TIMESTAMP,
    PRIMARY KEY (year, request, dim, code)
);
COMMENT ON TABLE meta_probe IS 'Probes: the query of a request filtered by one classifier code, used to resolve codes of names that are ambiguous or do not match the classifier list (see docs/en/sources.md).';
COMMENT ON COLUMN meta_probe.request IS 'Request name the probe belongs to (expenditure, revenue-t1, ...)';
COMMENT ON COLUMN meta_probe.dim IS 'Classifier filtered (dimension key)';
COMMENT ON COLUMN meta_probe.n_records IS '0 if the filtered query returned nothing';

CREATE TABLE meta_document (
    file        VARCHAR PRIMARY KEY,
    url         VARCHAR,
    title_hy    VARCHAR,
    title_en    VARCHAR,
    title_ru    VARCHAR,
    reports     VARCHAR,
    size_bytes  BIGINT,
    sha256      VARCHAR,
    fetched_at  TIMESTAMP
);
COMMENT ON TABLE meta_document IS 'PDF documents linked from the forms (guidelines on the application of the budget classification); stored in data/raw/documents.';

CREATE TABLE meta_label (
    context  VARCHAR NOT NULL,
    key      VARCHAR NOT NULL,
    hy       VARCHAR,
    en       VARCHAR,
    ru       VARCHAR,
    PRIMARY KEY (context, key)
);
COMMENT ON TABLE meta_label IS 'Labels of the source interface (column captions, form fields, options) with translations.';

------------------------------------------------------------------------------
-- dimensions
------------------------------------------------------------------------------
CREATE TABLE dim_period (
    period    VARCHAR PRIMARY KEY,
    months    INTEGER,
    sort      INTEGER,
    label_hy  VARCHAR,
    label_en  VARCHAR,
    label_ru  VARCHAR
);
COMMENT ON TABLE dim_period IS 'Periods of the report columns. All plans and executed amounts are cumulative from 1 January.';
COMMENT ON COLUMN dim_period.period IS 'q1 (January-March), h1 (January-June), m9 (January-September), year (January-December)';

CREATE TABLE dim_functional (
    code        VARCHAR PRIMARY KEY,
    level       INTEGER NOT NULL,
    level_name  VARCHAR,
    parent_code VARCHAR,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER
);
COMMENT ON TABLE dim_functional IS 'Functional classification of expenditures (based on COFOG): section (2 digits, «բաժին») -> group (4 digits, «խումբ») -> class (6 digits, «դաս»).';
COMMENT ON COLUMN dim_functional.level IS '1 section, 2 group, 3 class';
COMMENT ON COLUMN dim_functional.level_name IS 'section | group | class';
COMMENT ON COLUMN dim_functional.parent_code IS 'Code of the upper level (first 2 or 4 digits)';
COMMENT ON COLUMN dim_functional.name_hy IS 'Name in Armenian as in the classifier list of the latest year the code appears (in all dim_* tables: if the list gives the code without a name, the label of the result grid)';
COMMENT ON COLUMN dim_functional.name_en IS 'English translation (data/translations)';
COMMENT ON COLUMN dim_functional.name_ru IS 'Russian translation (data/translations)';
COMMENT ON COLUMN dim_functional.first_year IS 'First year the code appears in the classifier lists of the site';
COMMENT ON COLUMN dim_functional.last_year IS 'Last year the code appears in the classifier lists of the site';

CREATE TABLE dim_program (
    code        VARCHAR PRIMARY KEY,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER
);
COMMENT ON TABLE dim_program IS 'Expenditure programs/measures («Ծրագիր» on the site): 6-digit codes of the treasury system with the name of the budget program measure.';

CREATE TABLE dim_department (
    code        VARCHAR PRIMARY KEY,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER,
    in_expenditure BOOLEAN,
    in_revenue  BOOLEAN
);
COMMENT ON TABLE dim_department IS 'Departmental (administrative) classification: state bodies managing the budget appropriations / collecting revenues. 6-digit codes; 3xxxxx «Այլ մարմիններ» are other bodies.';
COMMENT ON COLUMN dim_department.in_expenditure IS 'Code appears in the expenditure classifier lists';
COMMENT ON COLUMN dim_department.in_revenue IS 'Code appears in the revenue classifier lists';

CREATE TABLE dim_economic (
    code          VARCHAR PRIMARY KEY,
    class_code    VARCHAR,
    category_code VARCHAR,
    group_code    VARCHAR,
    name_hy       VARCHAR,
    name_en       VARCHAR,
    name_ru       VARCHAR,
    first_year    INTEGER,
    last_year     INTEGER
);
COMMENT ON TABLE dim_economic IS 'Economic classification of expenditures: articles («Հոդված», 4 digits) as published by the site, with their upper levels (dim_economic_level).';
COMMENT ON COLUMN dim_economic.class_code IS 'First digit: 4 current expenditures, 5 expenditures on non-financial assets, 6 receipts from the sale of non-financial assets (negative expenditures), 7 technical articles';
COMMENT ON COLUMN dim_economic.category_code IS 'First 2 digits (e.g. 41 compensation of employees, 42 purchase of services and goods)';
COMMENT ON COLUMN dim_economic.group_code IS 'First 3 digits (e.g. 411 wages and salaries in cash)';

CREATE TABLE dim_economic_level (
    code        VARCHAR PRIMARY KEY,
    level       INTEGER,
    level_name  VARCHAR,
    parent_code VARCHAR,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR
);
COMMENT ON TABLE dim_economic_level IS 'Upper levels of the economic classification (class 1 digit, category 2 digits, group 3 digits). Not published by the site as data: Armenian names from the classification guidelines linked from the forms (meta_document), translations in src/arm_budget/reference.py.';
COMMENT ON COLUMN dim_economic_level.level IS '1 class, 2 category, 3 group';

CREATE TABLE dim_revenue_type (
    revenue_type INTEGER PRIMARY KEY,
    name_hy      VARCHAR,
    name_en      VARCHAR,
    name_ru      VARCHAR
);
COMMENT ON TABLE dim_revenue_type IS 'Types of revenue («ԵԿԱՄՈՒՏՆԵՐԻ ՏԵՍԱԿՆԵՐ», form field SITE_EBUDG). 0 = all revenues is used only for checks.';

CREATE TABLE dim_revenue_section (
    code        VARCHAR PRIMARY KEY,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER
);
COMMENT ON TABLE dim_revenue_section IS 'Revenue classification, upper level («Բաժին» on the revenue form, 2-digit codes: VAT from legal persons, excise tax on imports, ...).';

CREATE TABLE dim_revenue_group (
    code        VARCHAR PRIMARY KEY,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER
);
COMMENT ON TABLE dim_revenue_group IS 'Revenue classification, lower level («Խումբ», 4-digit codes). The codes do not start with the section code.';

CREATE TABLE dim_revenue_account (
    code        VARCHAR PRIMARY KEY,
    name_hy     VARCHAR,
    name_en     VARCHAR,
    name_ru     VARCHAR,
    first_year  INTEGER,
    last_year   INTEGER
);
COMMENT ON TABLE dim_revenue_account IS 'Treasury revenue accounts («Հաշիվ», 12-digit codes 900005xxxxxx): the finest level of the revenue report.';

CREATE TABLE dim_name (
    report      VARCHAR NOT NULL,
    dim         VARCHAR NOT NULL,
    code        VARCHAR NOT NULL,
    year        INTEGER NOT NULL,
    name_hy     VARCHAR,
    PRIMARY KEY (report, dim, code, year)
);
COMMENT ON TABLE dim_name IS 'Name of every classifier code in every year, as in the checkbox lists of the forms (names can change between years).';
COMMENT ON COLUMN dim_name.dim IS 'func_section | func_group | func_class | program | department | economic | rev_section | rev_group | rev_account';

CREATE TABLE dim_translation (
    context  VARCHAR NOT NULL,
    hy       VARCHAR NOT NULL,
    en       VARCHAR,
    ru       VARCHAR,
    PRIMARY KEY (context, hy)
);
COMMENT ON TABLE dim_translation IS 'Translation dictionary Armenian -> English / Russian (data/translations/<context>.csv). Machine-assisted translation, reviewed for consistency; the Armenian text is authoritative.';
COMMENT ON COLUMN dim_translation.context IS 'File the translation comes from: functional, program, department, economic, revenue, deficit, labels, ...';

------------------------------------------------------------------------------
-- facts
------------------------------------------------------------------------------
CREATE TABLE fact_expenditure (
    year              INTEGER NOT NULL,
    line_no           INTEGER NOT NULL,
    func_section_code VARCHAR,
    func_group_code   VARCHAR,
    func_class_code   VARCHAR,
    program_code      VARCHAR,
    department_code   VARCHAR,
    economic_code     VARCHAR,
    contract_line_id  INTEGER,
    q1_plan_kamd      DECIMAL(18, 4),
    q1_actual_kamd    DECIMAL(18, 4),
    h1_plan_kamd      DECIMAL(18, 4),
    h1_actual_kamd    DECIMAL(18, 4),
    m9_plan_kamd      DECIMAL(18, 4),
    m9_actual_kamd    DECIMAL(18, 4),
    year_plan_kamd    DECIMAL(18, 4),
    year_actual_kamd  DECIMAL(18, 4),
    request_id        VARCHAR,
    recid             INTEGER,
    PRIMARY KEY (year, line_no)
);
COMMENT ON TABLE fact_expenditure IS 'State budget expenditures at the finest level published: functional class x program/measure x department x economic article. Thousand AMD; plans and executed amounts cumulative from 1 January.';
COMMENT ON COLUMN fact_expenditure.line_no IS 'Number of the line within the year (order of the source tree, sorted by codes)';
COMMENT ON COLUMN fact_expenditure.func_section_code IS 'Functional section, 2 digits (dim_functional)';
COMMENT ON COLUMN fact_expenditure.func_group_code IS 'Functional group, 4 digits (dim_functional)';
COMMENT ON COLUMN fact_expenditure.func_class_code IS 'Functional class, 6 digits (dim_functional)';
COMMENT ON COLUMN fact_expenditure.program_code IS 'Program/measure, 6 digits (dim_program)';
COMMENT ON COLUMN fact_expenditure.department_code IS 'Department, 6 digits (dim_department)';
COMMENT ON COLUMN fact_expenditure.economic_code IS 'Economic article, 4 digits (dim_economic)';
COMMENT ON COLUMN fact_expenditure.contract_line_id IS 'Id of the line in the contract registry of the site (opens the contracts in fact_contract); NULL if the line has no contracts';
COMMENT ON COLUMN fact_expenditure.q1_plan_kamd IS 'Plan for January-March, thousand AMD';
COMMENT ON COLUMN fact_expenditure.q1_actual_kamd IS 'Executed in January-March, thousand AMD';
COMMENT ON COLUMN fact_expenditure.h1_plan_kamd IS 'Plan for January-June, thousand AMD';
COMMENT ON COLUMN fact_expenditure.h1_actual_kamd IS 'Executed in January-June, thousand AMD';
COMMENT ON COLUMN fact_expenditure.m9_plan_kamd IS 'Plan for January-September, thousand AMD';
COMMENT ON COLUMN fact_expenditure.m9_actual_kamd IS 'Executed in January-September, thousand AMD';
COMMENT ON COLUMN fact_expenditure.year_plan_kamd IS 'Annual plan, thousand AMD';
COMMENT ON COLUMN fact_expenditure.year_actual_kamd IS 'Executed since 1 January up to meta_year.as_of_date (the whole year for completed years), thousand AMD';
COMMENT ON COLUMN fact_expenditure.request_id IS 'Source request (meta_request)';
COMMENT ON COLUMN fact_expenditure.recid IS 'Row of the source grid (raw_grid_cell.recid)';

CREATE TABLE fact_revenue (
    year              INTEGER NOT NULL,
    revenue_type      INTEGER NOT NULL,
    line_no           INTEGER NOT NULL,
    line_kind         VARCHAR NOT NULL,
    rev_section_code  VARCHAR,
    rev_group_code    VARCHAR,
    department_code   VARCHAR,
    rev_account_code  VARCHAR,
    q1_plan_kamd      DECIMAL(18, 4),
    q1_actual_kamd    DECIMAL(18, 4),
    h1_plan_kamd      DECIMAL(18, 4),
    h1_actual_kamd    DECIMAL(18, 4),
    m9_plan_kamd      DECIMAL(18, 4),
    m9_actual_kamd    DECIMAL(18, 4),
    year_plan_kamd    DECIMAL(18, 4),
    year_actual_kamd  DECIMAL(18, 4),
    request_id        VARCHAR,
    recid             INTEGER,
    PRIMARY KEY (year, revenue_type, line_no)
);
COMMENT ON TABLE fact_revenue IS 'State budget revenues at the finest level published: revenue type x section x group x department x treasury account. Thousand AMD; cumulative from 1 January. Most of the plan is set for the revenue type as a whole: it is in the row line_kind = unallocated; plans of the accounts are partial.';
COMMENT ON COLUMN fact_revenue.line_kind IS 'line (an account of the source) | unallocated (the part of the total plan of the revenue type that is not distributed to the accounts; no codes, one row per year and type)';
COMMENT ON COLUMN fact_revenue.revenue_type IS '1 taxes and duties, 2 official grants, 3 other revenues (dim_revenue_type)';
COMMENT ON COLUMN fact_revenue.rev_section_code IS 'Revenue section, 2 digits (dim_revenue_section)';
COMMENT ON COLUMN fact_revenue.rev_group_code IS 'Revenue group, 4 digits (dim_revenue_group)';
COMMENT ON COLUMN fact_revenue.department_code IS 'Department administering the revenue (dim_department)';
COMMENT ON COLUMN fact_revenue.rev_account_code IS 'Treasury account, 12 digits (dim_revenue_account)';
COMMENT ON COLUMN fact_revenue.year_actual_kamd IS 'Received since 1 January up to meta_year.as_of_date, thousand AMD';

CREATE TABLE fact_deficit (
    year            INTEGER NOT NULL,
    line_no         INTEGER NOT NULL,
    label_hy        VARCHAR,
    label_en        VARCHAR,
    label_ru        VARCHAR,
    item_code       VARCHAR,
    row_kind        VARCHAR,
    level           INTEGER,
    parent_line_no  INTEGER,
    note_hy         VARCHAR,
    indent          INTEGER,
    in_totals_view  BOOLEAN,
    is_highlighted  BOOLEAN,
    q1_plan_kamd    DECIMAL(18, 2),
    q1_actual_kamd  DECIMAL(18, 2),
    h1_plan_kamd    DECIMAL(18, 2),
    h1_actual_kamd  DECIMAL(18, 2),
    m9_plan_kamd    DECIMAL(18, 2),
    m9_actual_kamd  DECIMAL(18, 2),
    year_plan_kamd  DECIMAL(18, 2),
    year_actual_kamd DECIMAL(18, 2),
    request_id      VARCHAR,
    recid           INTEGER,
    PRIMARY KEY (year, line_no)
);
COMMENT ON TABLE fact_deficit IS 'Sources of financing of the budget deficit, all lines of the report (SITE_DALL = 2), in the order of the source. The report is a formatted statement, not a classifier: only numbered lines add up (see row_kind).';
COMMENT ON COLUMN fact_deficit.label_hy IS 'Line label as published (leading spaces removed, see indent)';
COMMENT ON COLUMN fact_deficit.label_en IS 'English translation of the label (data/translations/deficit.csv)';
COMMENT ON COLUMN fact_deficit.label_ru IS 'Russian translation of the label (data/translations/deficit.csv)';
COMMENT ON COLUMN fact_deficit.item_code IS 'Position derived from the numbering: TOTAL, A / B (domestic / external sources), A.1, A.1.1, ...; NULL for detail lines';
COMMENT ON COLUMN fact_deficit.row_kind IS 'total | source (A, B) | item (1., 2.) | subitem (1.1) | detail (unnumbered breakdown of the preceding numbered line: bodies, companies, loans) | note (separator rows «այդ թվում» including, «որից» of which; no values)';
COMMENT ON COLUMN fact_deficit.level IS '0 total, 1 source, 2 item, 3 subitem, 4 detail';
COMMENT ON COLUMN fact_deficit.parent_line_no IS 'line_no of the numbered line this line belongs to';
COMMENT ON COLUMN fact_deficit.note_hy IS 'Separator above the detail line: «այդ թվում» (including) or «որից» (of which)';
COMMENT ON COLUMN fact_deficit.indent IS 'Number of leading spaces of the label (nesting of detail lines in the source)';
COMMENT ON COLUMN fact_deficit.in_totals_view IS 'TRUE if the line is also shown in the totals view (SITE_DALL = 1)';
COMMENT ON COLUMN fact_deficit.is_highlighted IS 'TRUE if the source highlights the row (numbered lines)';
COMMENT ON COLUMN fact_deficit.year_actual_kamd IS 'Since 1 January up to meta_year.as_of_date, thousand AMD';

CREATE TABLE fact_contract (
    year              INTEGER NOT NULL,
    contract_line_id  INTEGER NOT NULL,
    seq               INTEGER NOT NULL,
    partner_hy        VARCHAR,
    partner_en        VARCHAR,
    partner_ru        VARCHAR,
    start_date        DATE,
    end_date          DATE,
    amount_kamd       DECIMAL(18, 2),
    paid_kamd         DECIMAL(18, 2),
    n_files           INTEGER,
    PRIMARY KEY (year, contract_line_id, seq)
);
COMMENT ON TABLE fact_contract IS 'Contracts financed from an expenditure line (popup «Պայմանագրի դիտում» of the site). A contract financed from several lines appears once per line.';
COMMENT ON COLUMN fact_contract.contract_line_id IS 'Expenditure line (fact_expenditure.contract_line_id)';
COMMENT ON COLUMN fact_contract.seq IS 'Order of the contract on the page';
COMMENT ON COLUMN fact_contract.partner_hy IS 'Counterparty as published («Գործընկեր»)';
COMMENT ON COLUMN fact_contract.partner_en IS 'Counterparty transliterated to Latin script, legal form abbreviation translated (automatic)';
COMMENT ON COLUMN fact_contract.partner_ru IS 'Counterparty transliterated to Cyrillic, legal form abbreviation translated (automatic)';
COMMENT ON COLUMN fact_contract.amount_kamd IS 'Contract amount («Պայմ.գումարը»), thousand AMD';
COMMENT ON COLUMN fact_contract.paid_kamd IS 'Paid from this expenditure line («Վճարված գումար»), thousand AMD';

CREATE TABLE fact_contract_file (
    year              INTEGER NOT NULL,
    contract_line_id  INTEGER NOT NULL,
    seq               INTEGER NOT NULL,
    file_no           INTEGER NOT NULL,
    url               VARCHAR,
    host              VARCHAR,
    link_text         VARCHAR,
    PRIMARY KEY (year, contract_line_id, seq, file_no)
);
COMMENT ON TABLE fact_contract_file IS 'Links to the documents of a contract: the contract in the e-procurement system (armeps.am) and scans stored on the site (xml/storage/*.pdf). Files are not downloaded.';

------------------------------------------------------------------------------
-- staging and raw
------------------------------------------------------------------------------
CREATE TABLE stg_report_node (
    request_id    VARCHAR NOT NULL,
    recid         INTEGER NOT NULL,
    year          INTEGER,
    level         INTEGER,
    dim           VARCHAR,
    label_hy      VARCHAR,
    parent_recid  INTEGER,
    code          VARCHAR,
    code_method   VARCHAR,
    is_leaf       BOOLEAN,
    q1_plan_kamd      DECIMAL(18, 4),
    q1_actual_kamd    DECIMAL(18, 4),
    h1_plan_kamd      DECIMAL(18, 4),
    h1_actual_kamd    DECIMAL(18, 4),
    m9_plan_kamd      DECIMAL(18, 4),
    m9_actual_kamd    DECIMAL(18, 4),
    year_plan_kamd    DECIMAL(18, 4),
    year_actual_kamd  DECIMAL(18, 4),
    PRIMARY KEY (request_id, recid)
);
COMMENT ON TABLE stg_report_node IS 'Every row of the expenditure and revenue trees (grand total, subtotals of every level, leaves) with the resolved code.';
COMMENT ON COLUMN stg_report_node.level IS '-1 grand total, 0 .. n-1 classifier levels in the order of the grouping';
COMMENT ON COLUMN stg_report_node.dim IS 'Classifier of the level';
COMMENT ON COLUMN stg_report_node.label_hy IS 'Label as in the grid (punctuation removed by the site)';
COMMENT ON COLUMN stg_report_node.code_method IS 'name (unique match with the classifier list of the year) | name_other_year (unique match with the list of another year) | probe (filtered query) | NULL (unresolved)';

CREATE TABLE raw_grid_cell (
    request_id  VARCHAR NOT NULL,
    recid       INTEGER NOT NULL,
    field       VARCHAR NOT NULL,
    caption     VARCHAR,
    value       VARCHAR,
    PRIMARY KEY (request_id, recid, field)
);
COMMENT ON TABLE raw_grid_cell IS 'Lossless copy of every non-empty cell of every report grid (all requests in meta_request), values as strings exactly as in the source.';
COMMENT ON COLUMN raw_grid_cell.field IS 'w2ui field name: c2 ... c20';
COMMENT ON COLUMN raw_grid_cell.caption IS 'Column caption of the field';

CREATE TABLE raw_grid_row (
    request_id  VARCHAR NOT NULL,
    recid       INTEGER NOT NULL,
    style       VARCHAR,
    PRIMARY KEY (request_id, recid)
);
COMMENT ON TABLE raw_grid_row IS 'Rows of the report grids with the row style of the source (highlighted rows).';
