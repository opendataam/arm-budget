# Data quality

**English** | [Հայերեն](../hy/data_quality.md) | [Русский](../ru/data_quality.md)

The checks run on every build (`sql/qc.sql`) and are stored in the database. Summary:

```sql
SELECT * FROM qc_summary;
```

## Results of the latest build

<!-- QC_RESULTS -->
Collected on 2026-11-05; the latest data refer to 2026-11-04.

| check | status | issues | meaning |
|---|---|---|---|
| `balance` | info | 2 | expenditure plan − revenue plan ≠ deficit plan (> 0.1 %) |
| `contract_link` | OK | 0 | contract lines without contract pages / pages without a line |
| `contract_paid` | info | 53 | lines where payments under contracts exceed the executed amount |
| `missing_translation` | OK | 0 | names without an English or Russian translation |
| `renamed_code` | info | 20 | codes whose name changed between years |
| `revenue_types` | OK | 0 | revenue types do not add up to all revenues |
| `revenue_unallocated` | info | 6 | year × revenue type with plan not distributed to the accounts |
| `site_total` | OK | 0 | start page totals differ from the database |
| `tree_subtotal` | OK | 0 | published subtotals differ from the sum of their children |
| `tree_total` | OK | 0 | fact rows do not add up to the published grand total |
| `unresolved_code` | OK | 0 | rows of the fact trees without a classifier code |
<!-- /QC_RESULTS -->

## Checks

| check | table | what is checked |
|---|---|---|
| `unresolved_code` | `qc_unresolved_code` | every row of the expenditure tree and of the revenue trees (types 1–3) has a classifier code |
| `tree_total` | `qc_tree_total` | the leaves of every tree add up to the grand total published by the site (annual plan and execution) |
| `tree_subtotal` | `qc_tree_subtotal` | every subtotal published by the site equals the sum of its children |
| `revenue_types` | `qc_revenue_types` | taxes and duties + official grants + other revenues = all revenues (`SITE_EBUDG` 1+2+3 vs 0) |
| `site_total` | `qc_site_total` | the totals in the menu of the start page = annual plans of the latest year in the database |
| `balance` | `qc_balance` | expenditure plan − revenue plan = planned deficit, for every year |
| `contract_link` | `qc_contract_link` | every expenditure line with contracts has contract data and every contract page belongs to a line |
| `contract_paid` | `qc_contract_paid` | (info) lines where payments under contracts exceed the executed amount of the line |
| `missing_translation` | `qc_missing_translation` | every Armenian name has an English and a Russian translation |
| `renamed_code` | `qc_renamed_code` | (info) codes whose name differs between years |

## Quirks and issues of the source

1. **Names only, no codes, in the results.** Codes come from the checkbox lists of the forms; ≈5 % of the rows
   need a probe (filtered query) because a name is shared by several codes or differs from the list
   (see [sources.md](sources.md#classifier-codes-why-probes-are-needed)).
2. **Codes without a name in the lists.** The classifier lists of a year contain a few codes with an empty name
   (programs `004077`, `004576`, `004617`, revenue group `1688`, several revenue accounts), while the results show
   their names (e.g. the program «Ուսուցչի օրվա առթիվ … պարգևատրում», the revenue group of state duties for the
   trade in diamonds). The probes test these codes first; the `dim_*` tables take the name from the result grid.
3. **Revenue plans with "all revenues".** With `SITE_EBUDG = 0` the site shows plans only for the grand total;
   detail plans are published only per revenue type, so the facts are built from types 1–3.
4. **Revenue plans are set for the type as a whole.** ≈97 % of the annual plan of taxes and duties and 100 % of
   the plan of official grants are not distributed to sections, groups or accounts (other revenues are fully
   distributed). The build keeps this part as one row per year and type with `line_kind = 'unallocated'`
   (`qc_revenue_unallocated`); many accounts therefore have execution without a plan. Compare plan and execution
   of revenues at the level of the type.
5. **Punctuation and spelling.** The grid drops commas, semicolons and quotes; the lists keep them but contain
   wrapped lines (`\n` inside words), Latin look-alike letters (`u` for `ս`) and occasional typos. Names in the
   database are cleaned of line breaks; the original spelling is kept.
6. **Names change between years** (renamed ministries, reworded programs) and codes are reused for renamed
   bodies; `dim_*` keep the latest name, `dim_name` every name by year (`qc_renamed_code`). A renamed body may
   also get a new code (e.g. the Ministry of Economy `104004` and `104007`).
7. **Live data.** The current year is updated daily; requests made minutes apart may differ slightly. Contract
   pages are downloaded after the report queries, so their payments can be a little more recent than
   `fact_expenditure`.
8. **The deficit statement is not additive.** Detail lines are breakdowns of the numbered line above them
   (bodies, companies, loans) and may overlap; some labels carry leftovers of old years
   («ՀՀ 2017 թվականի պետական բյուջեի տարեսկզբի ազատ մնացորդ» in the 2024–2026 reports).
9. **Rounding.** Expenditure and revenue amounts have 4 decimals (thousand AMD), deficit amounts and Excel exports
   2 decimals; the `%` columns of the site are rounded to integers.
10. **Only three years.** The site drops the oldest year when a new one is added; older data exist only in the
    releases of this repository.
11. **Server instability.** The site sometimes resets connections or never answers a request; the collector
    retries (see [maintenance.md](maintenance.md)).
