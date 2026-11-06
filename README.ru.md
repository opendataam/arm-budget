# Государственный бюджет Армении: данные Министерства финансов в DuckDB

[English](README.md) | [Հայերեն](README.hy.md) | **Русский**

Сбор, нормализация и документирование данных о плане и исполнении **государственного бюджета
Республики Армения**, которые Министерство финансов публикует в «Интерактивном бюджете» («Ինտերակտիվ բյուջե»):
<https://budget.minfin.am:82/>.

У сайта есть только армянский интерфейс, а данные он показывает лишь через запросы к своей базе. Конвейер
собирает **всё**, что сайт публикует, за все доступные годы (последние три: 2024–2026):

* **расходы** на самом детальном уровне, который позволяет сайт: функциональная классификация (раздел → группа →
  класс) × программа/мероприятие × ведомство × статья экономической классификации, ≈3 600 бюджетных строк в год;
* **доходы** по видам (налоги и пошлины / официальные трансферты / прочие) × раздел × группа × ведомство ×
  казначейский счет, ≈450–480 строк в год;
* **финансирование дефицита** (внутренние и внешние источники, все строки отчета);
* **контракты**, оплачиваемые по каждой строке расходов (≈2 000 строк в год): контрагент, даты, сумма контракта,
  выплаченная сумма, ссылки на документы контракта;
* **классификаторы с кодами** за каждый год, методические указания в PDF по бюджетной классификации;

по каждой строке: план и исполнение за I квартал, январь–июнь, январь–сентябрь и год (тыс. драмов).

Результат — база данных DuckDB `data/arm_budget.duckdb` с кодами в таблицах фактов, **названиями всех
классификаторов на армянском, английском и русском языках**, полной копией всех исходных ячеек, проверками
качества данных и документацией на трех языках.

## Готовые данные: релизы

База данных и сырые данные в git не хранятся. Каждый запуск сбора публикуется как **релиз** репозитория
([Releases](https://github.com/opendataam/arm-budget/releases)) с тегом `data-YYYY-MM-DD` — датой сбора;
тег указывает на коммит кода, которым собрана база.

| файл релиза | содержимое |
|---|---|
| `arm_budget.duckdb.xz` | база данных DuckDB |
| `arm_budget-parquet.zip` | все таблицы и представления в Parquet + словарь данных |
| `arm_budget-raw.tar.xz` | сырые данные: страницы отчетов, экспорты Excel, пробные запросы, страницы контрактов, PDF (`raw/`) и манифесты (`catalog/`) |
| `SHA256SUMS` | контрольные суммы |

```bash
make install
make download            # latest release: database -> data/arm_budget.duckdb (SHA256 verified)
make lab                 # notebook with examples
```

Другие варианты: `make download-parquet`, `make download-raw` (затем `make build` пересоберет базу, не обращаясь
к сайту), конкретный снимок — `make download TAG=data-2026-11-05`. Без Python:
`curl -LO https://github.com/opendataam/arm-budget/releases/latest/download/arm_budget.duckdb.xz && xz -d arm_budget.duckdb.xz`.

**Сайт хранит только последние три года**: релизы также служат архивом лет, которые с него исчезают.

## Быстрый старт: собрать всё самостоятельно

```bash
make install   # creates .venv and installs the package with the dev + notebook extras (via uv if available; Python ≥ 3.10)
make all       # catalog → fetch → contracts → build → docs  (≈4–6 hours, mostly waiting for the site)
```

Или по шагам (в активированном окружении: `source .venv/bin/activate`):

```bash
python -m arm_budget catalog     # start page, forms of every report for every year (classifiers with codes), PDFs -> data/catalog
python -m arm_budget fetch       # report queries, Excel exports, code probes -> data/raw/reports, data/raw/probes
python -m arm_budget contracts   # contract pages of the expenditure lines -> data/raw/contracts
python -m arm_budget build       # -> data/arm_budget.duckdb
python -m arm_budget docs        # -> docs/data_dictionary.md, docs/{en,hy,ru}/inventory.md
```

Пример запроса:

```bash
duckdb -readonly data/arm_budget.duckdb -c "
  SELECT year, func_section_en, round(year_actual_kamd / 1e6, 1) AS executed_bn_amd
  FROM v_expenditure_by_function ORDER BY year, func_section_code"
```

## Jupyter notebook с примерами

[`docs/examples.ipynb`](docs/examples.ipynb): примеры запросов и графиков (хранится с результатами выполнения,
читается на GitHub). Текст ноутбука — на русском языке. `make lab` открывает его в JupyterLab (настройки в
[`scripts/jupyter_lab_config.py`](scripts/jupyter_lab_config.py)), `make notebook` выполняет его заново и сохраняет
результаты. Первая ячейка находит корень репозитория и открывает базу данных только для чтения. После
`make build` перезапустите ядро.

## Структура репозитория

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

## Документация

Документация доступна на английском ([docs/en](docs/en)), армянском ([docs/hy](docs/hy)) и русском
([docs/ru](docs/ru)) языках.

| документ | содержимое |
|---|---|
| [sources.md](docs/ru/sources.md) | сайт, его отчеты, как устроен его интерфейс запросов, особенности, единицы измерения, коды и пробные запросы |
| [database.md](docs/ru/database.md) | устройство базы данных: принципы, схема (ER), таблицы, представления, примеры запросов |
| [data_dictionary.md](docs/data_dictionary.md) | все таблицы и столбцы (генерируется) |
| [translations.md](docs/ru/translations.md) | названия на трех языках: словари, метод, как переводить новые названия |
| [data_quality.md](docs/ru/data_quality.md) | проверки качества данных и известные проблемы источника |
| [inventory.md](docs/ru/inventory.md) | годы, запросы, пробные запросы, контракты, документы (генерируется) |
| [maintenance.md](docs/ru/maintenance.md) | обновления, новый бюджетный год, изменения на сайте, устройство кода |
| [examples.ipynb](docs/examples.ipynb) | Jupyter notebook: примеры запросов и графиков |

## Основные таблицы

| таблица / представление | содержимое |
|---|---|
| `v_expenditure` / `fact_expenditure` | расходы: функциональный класс × программа × ведомство × статья экономической классификации, план и исполнение по периодам |
| `v_revenue` / `fact_revenue` | доходы: вид × раздел × группа × ведомство × казначейский счет |
| `v_deficit` / `fact_deficit` | источники финансирования дефицита |
| `v_contract` / `fact_contract`, `fact_contract_file` | контракты по строкам расходов и ссылки на их документы |
| `v_summary`, `v_expenditure_by_function`, `v_expenditure_by_department` | итоги |
| `dim_functional`, `dim_program`, `dim_department`, `dim_economic`, `dim_revenue_*` | классификаторы с названиями на hy / en / ru |
| `stg_report_node`, `raw_grid_cell` | все строки деревьев отчетов (включая промежуточные итоги) и все исходные ячейки |

## Особенности и ограничения

* Суммы приведены в тыс. драмов нарастающим итогом с 1 января; последний год неполный (`meta_year.as_of_date`).
* План доходов в основном задан для вида дохода в целом (`fact_revenue.line_kind = 'unallocated'`); сравнивайте
  план и исполнение доходов на уровне вида дохода.
* Суммируются только пронумерованные строки отчета о дефиците (`item_code IS NOT NULL`).
* Английские и русские названия — переводы с машинной поддержкой; армянские названия являются авторитетными.

## Источник

Данные: Министерство финансов Республики Армения, <https://budget.minfin.am:82/>. Лицензия на код репозитория
пока не выбрана.
