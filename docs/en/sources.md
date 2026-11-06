# Source: the "Interactive budget" of the Ministry of Finance

**English** | [Հայերեն](../hy/sources.md) | [Русский](../ru/sources.md)

## The site

<https://budget.minfin.am:82/> — «ՀՀ ՖԻՆԱՆՍՆԵՐԻ ՆԱԽԱՐԱՐՈՒԹՅՈՒՆ · ԻՆՏԵՐԱԿՏԻՎ ԲՅՈՒՋԵ» (Ministry of Finance of the
Republic of Armenia, Interactive budget). A web front end of the treasury system (LSFinance by LSoft) that shows the
plan and the execution of the **state budget** of the current and the two previous years. The interface exists only
in Armenian.

The left menu «ԲՅՈՒՋԵ» lists three reports with the annual plan of the latest year:

| menu item | page | report | database |
|---|---|---|---|
| Ծախսեր (expenditures) | `site_b` | expenditures by functional, program, departmental and economic classification; contracts | `fact_expenditure`, `fact_contract` |
| Եկամուտներ (revenues) | `site_d` | revenues by revenue type, section, group, department and treasury account | `fact_revenue` |
| Դեֆիցիտ (deficit) | `site_l` | sources of financing of the deficit | `fact_deficit` |

Years: the form offers only the **latest three years** (2024–2026 at the time of writing). Older years are not
available on the site. The current year is updated continuously (the expenditure export of 5 November 2026 was
«առ 04/11/26», i.e. as of the previous day); completed years refer to the end of December.

## Units and columns

All amounts are in **thousand AMD** («հազ. դրամներով»). Every result has the same 12 value columns:

| caption | meaning | database column |
|---|---|---|
| 1 եռամս. պլան / Գումարը / % | plan for Q1, executed, % | `q1_plan_kamd`, `q1_actual_kamd` |
| Կիսամ. պլան / Գումարը / % | plan for January–June, executed, % | `h1_plan_kamd`, `h1_actual_kamd` |
| 9 ամիս պլան / Գումարը / % | plan for January–September, executed, % | `m9_plan_kamd`, `m9_actual_kamd` |
| Տարի պլան / Գումարը / % | annual plan, executed since 1 January, % | `year_plan_kamd`, `year_actual_kamd` |

* Plans and executed amounts are **cumulative** from 1 January (H1 includes Q1).
* For the current year, the executed amount of a period that has not ended yet is the execution **up to the
  "as of" date** (`meta_year.as_of_date`); the "year" column is therefore the year-to-date execution.
* The `%` columns are not stored in the fact tables (they are `actual / plan`); they are kept in `raw_grid_cell`.
* The plan is the plan of the treasury system (the approved budget with the changes made during the year).
* The expenditure and revenue grids give amounts with 4 decimals, the deficit grid and the Excel exports with 2.

## How the site works

The site is a single-page application ([w2ui](https://w2ui.com/)) with server-side sessions:

1. `GET /` creates a session: the page contains a hidden `sessid` and sets the cookie `bcsession`. The menu items
   contain the annual plans of the latest year (`meta_site_total`).
2. `GET /param.php?sessid=…&lang=1&custid=0&page=site_b&isdoc=0` returns the **form** of a report.
3. The form is submitted as `POST /param.php` with `ACTION=VIEW` and:
   * `SITE_YEAR` — an index: `1` = the latest year, `2` = the previous one, … (the mapping changes when a new year
     is added; it is stored in `data/catalog/site.json` and `meta_year.year_index`);
   * filters — checkbox lists `mid[]` (department), `grp[]`, `sgrp[]`, `cls[]`, `prog[]`, `sub[]`, `acc[]`;
     no value = everything; the lists of the response are narrowed to the codes compatible with the filter;
   * grouping — selects `site_NN1` … `site_NN7` («Դասավորել ըստ դասակարգման», order of the classifiers);
   * revenue type `SITE_EBUDG` (revenues) or view `SITE_DALL` (deficit).
   The server stores the query in the session. After choosing a year, the checkbox lists contain the **classifiers
   of that year with their codes** — the only place where the site shows codes.
4. `GET /Popup.php?page=SITE_BG&uid=1&data=.&sessid=…` (expenditures; `SITE_DG` for revenues) returns the
   **result** of the stored query as a w2ui grid: a JavaScript literal with the column captions and the records.
   The deficit form returns its grid directly in the response of step 3.
5. `GET /xml/xmlopen.php?page=SITE_B_XLS&uid=1&lang=1` (`SITE_D_XLS`, `SITE_L_XLS`) writes an Excel export of the
   last result (XML Spreadsheet 2003) to `xml/temp/<id>.xls` and returns a link to it. Its title contains the date
   the data refer to: «ԲՅՈՒՋԵ ԾԱԽՍԵՐ առ 04/11/26 - հազ. դրամներով».
6. `GET /Popup.php?page=SITE_C&uid=1&data=<PARAM>{line};{year index};</PARAM>` returns the **contracts** of an
   expenditure line (the line id is column `c20` of a result grouped by «Պայմանագրեր»).

The collector uses one session at a time, waits 0.5 s between requests, does not reuse connections (the server
silently drops idle keep-alive connections, and a request sent on such a connection hangs) and retries failed
requests. The full expenditure tree takes 30 s – 5 minutes to render.

## Reports

### Expenditures (`site_b`)

Classifiers (checkbox lists and "group by" options):

| list | group option | classifier | codes | table |
|---|---|---|---|---|
| `grp[]` | 1 Բաժին | functional section | 2 digits | `dim_functional` (level 1) |
| `sgrp[]` | 2 Խումբ | functional group | 4 digits | `dim_functional` (level 2) |
| `cls[]` | 3 Դաս | functional class | 6 digits | `dim_functional` (level 3) |
| `prog[]` | 4 Ծրագիր | program/measure | 6 digits | `dim_program` |
| `mid[]` | 5 Գերատեսչական դասակարգում | department | 6 digits | `dim_department` |
| `sub[]` | 6 Հոդված | economic article | 4 digits | `dim_economic` |
| — | 7 Պայմանագրեր | contracts (line id) | — | `fact_contract` |

A query **grouped by all six classifiers** returns the finest data the site publishes, as a **tree** in depth-first
order: the grand total, then section → group → class → program → department → article; each row carries the label
of its own level only, siblings are sorted by code. The rows of the last level are the budget lines
(`fact_expenditure`), the others are subtotals (`stg_report_node`).

A query grouped by **contracts** returns a flat list of the lines that have contracts, each with all six labels
and the line id; this links `fact_expenditure.contract_line_id` to the contract pages.

The program list («Ֆունկցիոնալ դասակարգման ծրագիր») has 6-digit codes of the treasury system (e.g. `004828`);
the names are those of the program measures of the budget law.

The form links two PDF guidelines (annexes 16 and 17 to the order of the Minister of Finance and Economy of 9 January
2007 N 5-Ն): the economic classification of current expenditures (class 400000) and of expenditures on non-financial
assets (class 500000). The upper levels of the economic classification in `dim_economic_level` come from them.

### Revenues (`site_d`)

| list | group option | classifier | codes | table |
|---|---|---|---|---|
| `grp[]` | 1 Բաժին | revenue section (VAT from legal persons, excise tax on imports, …) | 2 digits | `dim_revenue_section` |
| `sgrp[]` | 2 Խումբ | revenue group | 4 digits | `dim_revenue_group` |
| `mid[]` | 3 Գերատեսչական դասակարգում | department administering the revenue | 6 digits | `dim_department` |
| `acc[]` | 4 Հաշիվ | treasury revenue account | 12 digits | `dim_revenue_account` |

`SITE_EBUDG` («ԵԿԱՄՈՒՏՆԵՐԻ ՏԵՍԱԿՆԵՐ») selects the revenue type: `0` all revenues, `1` taxes and duties,
`2` official grants, `3` other revenues. **Important quirk:** with `0` only the grand total carries a plan, all
detail rows have a plan of 0; the plans of the detail rows are published only per type. The collector therefore
queries all four; facts are built from types 1–3 (`fact_revenue.revenue_type`), type 0 is kept for the check that
the types add up (`qc_revenue_types`).

**Most of the revenue plan is not distributed to the accounts.** Even per type, ≈97 % of the annual plan of taxes
and duties and all of the plan of official grants are set only at the level of the type (the grand total of the
result); the plans of the accounts cover the rest. Execution is always by account. The build stores the
difference as one row per year and type with `line_kind = 'unallocated'` (no codes), so that sums over
`fact_revenue` equal the published totals (`qc_revenue_unallocated`). Compare plan and execution at the level of
the revenue type, not by account.

The form links annex 19 of the same order (current revenues, class 700000).

### Deficit (`site_l`)

`SITE_DALL` («ՏԵՍԱԿ»): `1` totals only (≈20 lines), `2` all lines (≈80–100). The report is a formatted statement of
the sources of financing of the deficit: total, A. domestic sources, B. external sources, numbered items (1., 1.1)
and unnumbered detail lines (bodies, companies, loans) introduced by «այդ թվում» (including) or «որից» (of which).
Negative values are shown in parentheses. The collector stores all lines (`fact_deficit`) with the structure
derived from the numbering (`item_code`, `row_kind`, `parent_line_no`); see [database.md](database.md).

### Contracts (`SITE_C`)

For every expenditure line with contracts: counterparty («Գործընկեր»), contract start and end dates, contract
amount and amount paid from this line (thousand AMD), and links to documents — the contract in the e-procurement
system `armeps.am` and scans stored on the site (`xml/storage/*.pdf`). The documents themselves are not downloaded
(`fact_contract_file` keeps the links). A contract paid from several lines appears once per line.

## Classifier codes: why probes are needed

The result grids contain **only names, never codes**. Codes are taken from the checkbox lists of the form for the
same year. Matching is done by letters and digits only, because the grid drops commas and other punctuation
(«Օրենսդիր և գործադիր մարմիններ, պետական կառավարում» in the list vs. «… մարմիններ պետական կառավարում» in the grid)
and prefixes economic articles with «- ».

Name matching resolves ~95 % of the rows. The rest are names shared by several codes (five departments called
«Այլ մարմիններ», economic articles 4221/4229 both called «Գործուղումների և շրջագայությունների ծախսեր», old and new
codes of a renamed ministry) or labels that do not match any list name (typos, different wording). For those the
collector runs a **probe**: the same query filtered by one candidate code (`mid[]=301022`, …). In the probe result
every row of that classifier level has that code; it is matched to the row of the full tree with the same labels on
the path and the same amounts. Probes are stored in `data/raw/probes` and listed in `meta_probe`; the method used
for every row is in `stg_report_node.code_method`. After the probes all codes of the fact rows are resolved
(`qc_unresolved_code`).

## Raw data on disk

| path | contents |
|---|---|
| `data/catalog/site.json` | menu totals, years and their `SITE_YEAR` indexes |
| `data/catalog/classifiers/<report>_<year>.json` | form of a report for a year: classifier lists (code, name), options |
| `data/catalog/requests.json` | every report request: parameters, file, rows, content hash, "as of" date |
| `data/catalog/probes.json` | every probe |
| `data/catalog/contracts/<year>.csv` | expenditure lines with contracts, number of contracts, content hash |
| `data/catalog/documents.json` | PDF documents |
| `data/raw/site/` | start page, form pages per report and year (gzip HTML) |
| `data/raw/reports/<year>/` | result pages (`*.html.gz`) and Excel exports (`*.export.xml.gz`) |
| `data/raw/probes/<year>/<request>/` | probe results |
| `data/raw/contracts/<year>/<line>.html.gz` | contract pages |
| `data/raw/documents/` | PDF guidelines |

The manifests in `data/catalog` are versioned in git (`content_sha256` does not depend on the session id, so the
git diff shows real changes of the data); `data/raw` is published in the releases.
