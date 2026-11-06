# Translations: names in Armenian, English and Russian

**English** | [Հայերեն](../hy/translations.md) | [Русский](../ru/translations.md)

The site publishes names only in Armenian. The database has every name in three languages:

| what | Armenian | English / Russian | where |
|---|---|---|---|
| classifiers (functional, programs, departments, economic articles, revenue sections, groups, accounts) | `name_hy` from the forms | `name_en`, `name_ru` from the dictionaries | `dim_*` |
| deficit lines | `label_hy` | `label_en`, `label_ru` | `fact_deficit` |
| interface of the site (captions, options) | `hy` | `en`, `ru` | `meta_label` |
| report names, periods, revenue types, upper levels of the economic classification | — | — | `src/arm_budget/reference.py` |
| contract counterparties | `partner_hy` | `partner_en`, `partner_ru` — **transliteration**, not translation | `fact_contract` |

## Dictionaries

`data/translations/<context>.csv` (versioned in git), columns `hy,en,ru`:

| file | names |
|---|---|
| `functional.csv` | functional classification (sections, groups, classes) |
| `program.csv` | programs / measures |
| `department.csv` | departments (state bodies) |
| `economic.csv` | economic articles |
| `revenue.csv` | revenue sections, groups and treasury accounts |
| `deficit.csv` | lines of the deficit report |
| `labels.csv` | interface of the site |

The build looks a name up by its Armenian text in the dictionary of its context (then in any dictionary),
comparing letters and digits only — differences in punctuation, spaces and case do not matter. All dictionaries
are loaded into `dim_translation`.

The terms and the style are fixed in [GLOSSARY.md](../../data/translations/GLOSSARY.md): COFOG names for the
functional classification, «ՀՀ» = "RA" / «РА», «միջոցառում» = "measure" / «мероприятие», sentence case, etc.

## How the translations were made

The first version of the dictionaries (≈2 300 names for 2024–2026) was produced with a large language model
(Claude) in batches, following the glossary, and checked automatically (every Armenian name kept unchanged, both
translations present). Abbreviations whose expansion is not certain were kept or transliterated. The Armenian text
remains authoritative: the translations are meant for search and reading, not as official names. Corrections are
welcome — edit the CSV and rebuild.

Counterparties of contracts (≈ companies and individuals) are transliterated automatically
(`src/arm_budget/translit.py`): Latin script by the common Armenian passport / BGN-PCGN practice, Cyrillic by the
usual Russian rendering; legal forms are translated (ՓԲԸ → CJSC / ЗАО, ՍՊԸ → LLC / ООО, ԱՁ → IE / ИП, …), and the
dashes that the site uses instead of quotation marks are turned back into quotes.

## New names

When a new year appears on the site, new programs, accounts and lines appear with it. Names without a translation
are listed in `qc_missing_translation` (and the check `missing_translation` in `qc_summary` becomes `warn`):

```bash
make build
python -m arm_budget translations           # -> data/translations/pending/<context>-NNN.csv (hy filled, en/ru empty)
# fill the en and ru columns: by hand, or with a machine translation following GLOSSARY.md, then review
python -m arm_budget translations --merge   # merges the filled rows into data/translations/<context>.csv
make build docs
```

Files in `pending/` are not versioned; a file is removed after all its rows are merged.
