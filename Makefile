VENV ?= .venv
# The project virtualenv is used when it exists: Homebrew/Debian Python forbid
# system-wide `pip install` (PEP 668). Override with `make ... PY=python3`.
PY ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
UV := $(shell command -v uv 2>/dev/null)
RUN = PYTHONPATH=src $(PY) -m arm_budget

.PHONY: help install all catalog fetch contracts build docs translations notebook lab release-pack release download download-raw download-parquet test lint clean

help:
	@echo "make install      create $(VENV) and install the package with dev + notebook extras (editable)"
	@echo "make all          full pipeline: catalog, fetch, contracts, build, docs"
	@echo "make catalog      start page, report forms per year (classifiers with codes), PDF documents -> data/catalog"
	@echo "make fetch        report queries, Excel exports and code probes for every year -> data/raw/reports"
	@echo "make contracts    contract pages of the expenditure lines -> data/raw/contracts"
	@echo "make build        (re)build data/arm_budget.duckdb"
	@echo "make docs         regenerate docs/data_dictionary.md and docs/*/inventory.md"
	@echo "make translations write names without a translation to data/translations/pending"
	@echo "make notebook     execute docs/examples.ipynb against the database and save outputs"
	@echo "make lab          open docs/examples.ipynb in Jupyter Lab (interactive)"
	@echo "make download     get the latest data snapshot (database) from GitHub releases"
	@echo "make download-raw get the raw data of the latest snapshot (then: make build)"
	@echo "make download-parquet  get every table as Parquet -> data/parquet"
	@echo "make release-pack pack the snapshot into data/release/<tag> (no upload)"
	@echo "make release      pack and publish the snapshot as a GitHub release (needs gh, clean pushed HEAD)"
	@echo "make test         run tests"

install:
ifdef UV
	$(UV) venv --allow-existing $(VENV)
	$(UV) pip install --python $(VENV)/bin/python -e '.[dev,notebook]'
else
	python3 -m venv $(VENV)
	$(VENV)/bin/python -m pip install -e '.[dev,notebook]'
endif

all: catalog fetch contracts build docs

catalog:
	$(RUN) catalog

fetch:
	$(RUN) fetch

contracts:
	$(RUN) contracts

build:
	$(RUN) build

docs:
	$(RUN) docs

translations:
	$(RUN) translations

# needs the notebook extras (make install)
notebook:
	$(PY) scripts/run_notebook.py docs/examples.ipynb

# interactive: opens the browser on the notebook; settings in scripts/jupyter_lab_config.py; stop with Ctrl+C
lab:
	$(VENV)/bin/jupyter trust docs/examples.ipynb
	$(VENV)/bin/jupyter lab --config scripts/jupyter_lab_config.py docs/examples.ipynb

# data snapshots in GitHub releases (src/arm_budget/release.py); TAG=data-YYYY-MM-DD to pick one
TAG ?= latest

download:
	$(RUN) download --tag $(TAG) --part db

download-raw:
	$(RUN) download --tag $(TAG) --part raw

download-parquet:
	$(RUN) download --tag $(TAG) --part parquet

release-pack:
	$(RUN) release --pack-only

release:
	$(RUN) release

test:
	PYTHONPATH=src $(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests scripts

clean:
	rm -f data/arm_budget.duckdb data/*.building.duckdb
