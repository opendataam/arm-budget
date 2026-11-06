# Maintenance

**English** | [Հայերեն](../hy/maintenance.md) | [Русский](../ru/maintenance.md)

## Regular update

On a new machine, first restore the raw data of the latest snapshot (contract pages of completed years are then
not downloaded again):

```bash
make install download-raw
```

Then:

```bash
make catalog fetch contracts build docs test
git add -A && git commit -m "data: update to $(date +%F)" && git push
make release            # a new data-<collection date> release with the database, Parquet and raw data
```

* `catalog` reads the start page and the forms of every report for every year: years, classifier lists with codes,
  PDF documents (`data/catalog/site.json`, `data/catalog/classifiers/*.json`, `data/catalog/documents.json`).
  Changes show up in `git diff` — a convenient way to notice that something changed on the site. The step also
  checks that the "group by" options still have the expected labels (`warnings` in `site.json`).
* `fetch` runs every report query for every year (≈15 queries + probes per year, 10–30 minutes in total: the full
  expenditure tree takes up to 5 minutes). Probes are re-run with their tree, because they are matched by amounts.
  It can be narrowed down: `python -m arm_budget fetch --report revenue --years 2026`.
* `contracts` downloads the contract page of every expenditure line with contracts (≈2 000–2 300 per year;
  most take ≈1 s, pages of lines with thousands of contracts take minutes; ≈3–5 hours for three years). Pages
  already on disk are kept, except for the latest year (`--refresh-years 1`), whose contracts and payments change
  every day: its pages are downloaded again when older than 12 hours (`--max-age-hours`). The manifest is written
  every 100 pages, so an interrupted run continues where it stopped; a page that does not answer within 45 s
  (two attempts) is requested again in the next pass (up to three passes); `--force` downloads everything again.
* `build` recreates the whole database (≈1 minute) and prints `qc_summary`; `docs` regenerates
  `docs/data_dictionary.md` and `docs/*/inventory.md`.
* Check `SELECT * FROM qc_summary` (see [data_quality.md](data_quality.md)). If `missing_translation` is `warn`,
  translate the new names (see [translations.md](translations.md)) and rebuild.
* `release` requires a clean working tree and a pushed `HEAD` (the release tag is put on that commit), and `gh`
  with write access to the repository. The default tag is `data-<date of the latest report request>`.

Recommended frequency: monthly; at least once in January–February, before the site drops the oldest year
(the site keeps three years; the releases of this repository are the only archive of older years).

## When a new year appears

The site adds the new budget year at the top of the year list, so the `SITE_YEAR` indexes of the other years
change (`1` is always the latest year). The collector reads the mapping from the form on every `catalog` run, so
nothing needs to be changed in the code. The oldest year disappears from the site: keep its raw data (the release
archives) if you need it in later builds — the build uses only what is in `data/raw` and `data/catalog`.

Expect many new names (programs, accounts, deficit lines): translate them (see above).

## What to do if…

**A request fails or hangs.** The server resets long connections and sometimes keeps a request without answering.
The client retries every request (5 attempts with growing pauses), uses a new connection for every request and has
read timeouts of 120 s (400 s for result pages, `config.HTTP_RESULT_TIMEOUT`). A query whose result has no grid or
has an unexpected grouping is repeated in a new session. Run the step again — it continues where it failed for
contracts; reports are always re-queried.

**Codes are unresolved** (`qc_unresolved_code`). The probes did not find a code for a label. Look at the label in
`stg_report_node` and at the classifier list of the year (`data/catalog/classifiers/<report>_<year>.json`). Usually
the site renamed something; running `fetch` again for that year/report re-runs the probes (the 5 most similar unused codes are probed for a label without a matching name,
widening the set of candidate codes). If the label has no counterpart in the list at all, the row stays without a
code; the amounts are still in the facts.

**The grouping labels changed** (`warnings` in `data/catalog/site.json`, or a request fails with
`grouping … != …`). Update `group_value` / `group_label` of the dimensions in `src/arm_budget/config.py`.

**A new revenue type, deficit view or report** appears in the forms. The options are recorded in
`data/catalog/classifiers/*.json` (`selects`); add them to `config.REVENUE.extra` / `config.DEFICIT.extra` or a new
`Report` in `config.py`, and the corresponding parsing in `build.py`.

**The deficit statement gets a new numbering style.** The structure is derived in `parsers/deficit.py`
(regular expressions for `Ա.`, `1.`, `1.1`); unrecognised lines become `detail` lines.

**A page layout changes.** All parsers are small and covered by tests with fixtures (`tests/test_parsers.py`):
grid (`parsers/grid.py`), forms (`parsers/forms.py`), contracts (`parsers/contracts.py`), exports
(`parsers/xls_export.py`).

## Code layout

| module | role |
|---|---|
| `config.py` | paths, URL, HTTP settings, definitions of the reports and classifiers |
| `site.py` | client of the site: session, form, query, result, export, contracts; retries |
| `fetch.py` | steps `catalog`, `fetch`, `contracts`; manifests in `data/catalog` |
| `tree.py` | turns a grouped grid into a tree of nodes (and the flat list of contract lines) |
| `resolve.py` | classifier codes by name and by probes (used by `fetch` and `build`) |
| `build.py` | builds the DuckDB database |
| `translations.py`, `translit.py`, `reference.py` | dictionaries, transliteration, static trilingual reference data |
| `docs.py`, `release.py` | generated documentation, data snapshots in GitHub releases |
