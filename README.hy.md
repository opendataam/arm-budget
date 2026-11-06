# Հայաստանի պետական բյուջե. ՀՀ ֆինանսների նախարարության տվյալները DuckDB-ում

[English](README.md) | **Հայերեն** | [Русский](README.ru.md)

Հավաքագրում, նորմալացում և փաստաթղթավորում՝ **Հայաստանի Հանրապետության պետական բյուջեի** պլանի և կատարման
տվյալների, որոնք ՀՀ ֆինանսների նախարարությունը հրապարակում է «Ինտերակտիվ բյուջե» («Ինտերակտիվ բյուջե»)
կայքում՝ <https://budget.minfin.am:82/>։

Կայքն ունի միայն հայերեն ինտերֆեյս և տվյալները ցույց է տալիս բացառապես իր տվյալների բազայի հարցումների միջոցով։
Փոխակրիչը (pipeline) հավաքագրում է **այն ամենը**, ինչ կայքը հրապարակում է բոլոր հասանելի տարիների համար
(վերջին երեքը՝ 2024–2026).

* **ծախսեր**՝ կայքի թույլատրած ամենադետալ մակարդակով. գործառական դասակարգում (բաժին → խումբ → դաս) ×
  ծրագիր/միջոցառում × գերատեսչություն × տնտեսագիտական դասակարգման հոդված, տարեկան ≈3 600 բյուջետային տող.
* **եկամուտներ**՝ ըստ տեսակի (հարկեր և տուրքեր / պաշտոնական դրամաշնորհներ / այլ) × բաժին × խումբ × գերատեսչություն ×
  գանձապետական հաշիվ, տարեկան ≈450–480 տող.
* **դեֆիցիտի** ֆինանսավորում (ներքին և արտաքին աղբյուրներ, հաշվետվության բոլոր տողերը).
* յուրաքանչյուր ծախսային տողից վճարվող **պայմանագրեր** (տարեկան ≈2 000 տող). գործընկեր, ամսաթվեր, պայմանագրի
  գումար, վճարված գումար, պայմանագրի փաստաթղթերի հղումներ.
* յուրաքանչյուր տարվա **դասակարգիչները՝ իրենց կոդերով**, բյուջետային դասակարգման PDF ուղեցույցները.

յուրաքանչյուր տողի համար՝ պլան և կատարում առաջին եռամսյակի, հունվար–հունիսի, հունվար–սեպտեմբերի և տարվա համար
(հազ. դրամ)։

Արդյունքը DuckDB տվյալների բազա է՝ `data/arm_budget.duckdb`, որի փաստերի աղյուսակներում կոդեր են, **բոլոր
դասակարգիչների անվանումները՝ հայերեն, անգլերեն և ռուսերեն**, սկզբնական բոլոր բջիջների անկորուստ պատճենը, տվյալների
որակի ստուգումներ և փաստաթղթավորում երեք լեզվով։

## Պատրաստի տվյալներ. թողարկումներ (releases)

Տվյալների բազան և հումքային տվյալները git-ում չեն պահվում։ Հավաքագրման յուրաքանչյուր գործարկում հրապարակվում է որպես
պահոցի **թողարկում** (release)
([Releases](https://github.com/opendataam/arm-budget/releases)) `data-YYYY-MM-DD` պիտակով (tag)՝ հավաքագրման ամսաթվով.
պիտակը ցույց է տալիս կոդի այն կոմիտը, որով կառուցվել է տվյալների բազան։

| թողարկման ֆայլ | պարունակություն |
|---|---|
| `arm_budget.duckdb.xz` | DuckDB տվյալների բազա |
| `arm_budget-parquet.zip` | բոլոր աղյուսակներն ու ներկայացումները (views) Parquet ձևաչափով + տվյալների բառարան |
| `arm_budget-raw.tar.xz` | հումքային տվյալներ. հաշվետվությունների էջեր, Excel արտահանումներ, ստուգիչ հարցումներ, պայմանագրերի էջեր, PDF (`raw/`) և մանիֆեստներ (`catalog/`) |
| `SHA256SUMS` | վերահսկիչ գումարներ |

```bash
make install
make download            # latest release: database -> data/arm_budget.duckdb (SHA256 verified)
make lab                 # notebook with examples
```

Այլ տարբերակներ՝ `make download-parquet`, `make download-raw` (դրանից հետո `make build`-ը վերակառուցում է տվյալների
բազան՝ առանց կայքին դիմելու), կոնկրետ պատկեր՝ `make download TAG=data-2026-11-05`։ Առանց Python-ի՝
`curl -LO https://github.com/opendataam/arm-budget/releases/latest/download/arm_budget.duckdb.xz && xz -d arm_budget.duckdb.xz`։

**Կայքը պահում է միայն վերջին երեք տարին**՝ թողարկումները նաև արխիվ են այն տարիների համար, որոնք անհետանում են կայքից։

## Արագ մեկնարկ. ամեն ինչ կառուցել ինքնուրույն

```bash
make install   # creates .venv and installs the package with the dev + notebook extras (via uv if available; Python ≥ 3.10)
make all       # catalog → fetch → contracts → build → docs  (≈4–6 hours, mostly waiting for the site)
```

Կամ քայլ առ քայլ (ակտիվացված միջավայրում՝ `source .venv/bin/activate`).

```bash
python -m arm_budget catalog     # start page, forms of every report for every year (classifiers with codes), PDFs -> data/catalog
python -m arm_budget fetch       # report queries, Excel exports, code probes -> data/raw/reports, data/raw/probes
python -m arm_budget contracts   # contract pages of the expenditure lines -> data/raw/contracts
python -m arm_budget build       # -> data/arm_budget.duckdb
python -m arm_budget docs        # -> docs/data_dictionary.md, docs/{en,hy,ru}/inventory.md
```

Հարցման օրինակ.

```bash
duckdb -readonly data/arm_budget.duckdb -c "
  SELECT year, func_section_en, round(year_actual_kamd / 1e6, 1) AS executed_bn_amd
  FROM v_expenditure_by_function ORDER BY year, func_section_code"
```

## Jupyter notebook օրինակներով

[`docs/examples.ipynb`](docs/examples.ipynb). օրինակելի հարցումներ և գծապատկերներ (պահվում են արդյունքներով, կարելի է
կարդալ GitHub-ում)։ Նոթբուքի տեքստը՝ ռուսերեն։ `make lab`-ը բացում է այն JupyterLab-ում (կարգավորումները՝
[`scripts/jupyter_lab_config.py`](scripts/jupyter_lab_config.py)), `make notebook`-ը վերագործարկում է այն և պահպանում
արդյունքները։ Առաջին բջիջը գտնում է պահոցի արմատը և տվյալների բազան բացում միայն կարդալու ռեժիմով։ `make build`-ից հետո
վերագործարկեք միջուկը (kernel)։

## Պահոցի կառուցվածքը

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

## Փաստաթղթավորում

Փաստաթղթավորումը հասանելի է անգլերեն ([docs/en](docs/en)), հայերեն ([docs/hy](docs/hy)) և ռուսերեն
([docs/ru](docs/ru)) լեզուներով։

| փաստաթուղթ | պարունակություն |
|---|---|
| [sources.md](docs/hy/sources.md) | կայքը, նրա հաշվետվությունները, հարցումների ինտերֆեյսի աշխատանքը, առանձնահատկությունները, չափման միավորները, կոդերը և ստուգիչ հարցումները |
| [database.md](docs/hy/database.md) | տվյալների բազայի նախագծում. սկզբունքներ, սխեմա (ER), աղյուսակներ, ներկայացումներ (views), հարցումների օրինակներ |
| [data_dictionary.md](docs/data_dictionary.md) | բոլոր աղյուսակներն ու սյունակները (գեներացվում է) |
| [translations.md](docs/hy/translations.md) | անվանումներ երեք լեզվով. բառարաններ, մեթոդ, նոր անվանումների թարգմանություն |
| [data_quality.md](docs/hy/data_quality.md) | տվյալների որակի ստուգումներ և աղբյուրի հայտնի խնդիրներ |
| [inventory.md](docs/hy/inventory.md) | տարիներ, հարցումներ, ստուգիչ հարցումներ, պայմանագրեր, փաստաթղթեր (գեներացվում է) |
| [maintenance.md](docs/hy/maintenance.md) | թարմացումներ, նոր բյուջետային տարի, կայքի փոփոխություններ, կոդի կառուցվածք |
| [examples.ipynb](docs/examples.ipynb) | Jupyter notebook. հարցումների և գծապատկերների օրինակներ |

## Հիմնական աղյուսակներ

| աղյուսակ / ներկայացում (view) | պարունակություն |
|---|---|
| `v_expenditure` / `fact_expenditure` | ծախսեր. գործառական դաս × ծրագիր × գերատեսչություն × տնտեսագիտական հոդված, պլան և կատարում ըստ ժամանակաշրջանների |
| `v_revenue` / `fact_revenue` | եկամուտներ. տեսակ × բաժին × խումբ × գերատեսչություն × գանձապետական հաշիվ |
| `v_deficit` / `fact_deficit` | դեֆիցիտի ֆինանսավորման աղբյուրներ |
| `v_contract` / `fact_contract`, `fact_contract_file` | ծախսային տողերի պայմանագրեր և դրանց փաստաթղթերի հղումներ |
| `v_summary`, `v_expenditure_by_function`, `v_expenditure_by_department` | ամփոփումներ |
| `dim_functional`, `dim_program`, `dim_department`, `dim_economic`, `dim_revenue_*` | դասակարգիչներ՝ hy / en / ru անվանումներով |
| `stg_report_node`, `raw_grid_cell` | հաշվետվությունների ծառերի բոլոր տողերը (ներառյալ միջանկյալ գումարները) և սկզբնական բոլոր բջիջները |

## Զգուշացումներ

* Գումարները հազ. դրամով են, կուտակային՝ հունվարի 1-ից. վերջին տարին թերի է (`meta_year.as_of_date`)։
* Եկամուտների պլանը հիմնականում սահմանված է եկամտի տեսակի համար ամբողջությամբ (`fact_revenue.line_kind = 'unallocated'`).
  եկամուտների պլանն ու կատարումը համեմատեք եկամտի տեսակի մակարդակով։
* Դեֆիցիտի հաշվետվության մեջ միայն համարակալված տողերն են գումարվում (`item_code IS NOT NULL`)։
* Անգլերեն և ռուսերեն անվանումները մեքենայական աջակցությամբ կատարված թարգմանություններ են. հայերեն անվանումները
  հիմնականն են (authoritative)։

## Աղբյուր

Տվյալներ՝ Հայաստանի Հանրապետության ֆինանսների նախարարություն, <https://budget.minfin.am:82/>։ Պահոցի կոդի լիցենզիան
դեռ ընտրված չէ։
