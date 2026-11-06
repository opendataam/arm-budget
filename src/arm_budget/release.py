"""Data snapshots published as GitHub release assets.

The database and the raw data are too large and too volatile for git history,
so every data collection is published as a GitHub release of the repository:

* tag ``data-YYYY-MM-DD`` (date of the data collection), pointing to the code
  commit the database was built with;
* assets with stable names (so ``releases/latest/download/<name>`` always works):

  ===============================  ============================================
  ``arm_budget.duckdb.xz``         the DuckDB database
  ``arm_budget-parquet.zip``       every table and view as Parquet + data dictionary
  ``arm_budget-raw.tar.xz``        ``raw/`` (report pages, exports, probes, contracts, PDFs) and ``catalog/``
  ``SHA256SUMS``                   checksums of the assets
  ===============================  ============================================

Commands: ``release`` (pack + ``gh release create``), ``download`` (fetch,
verify checksums, unpack into ``data/``). Compression is xz (standard library),
so downloading needs no extra tools.
"""

from __future__ import annotations

import hashlib
import logging
import lzma
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

import duckdb
import requests

from . import config

log = logging.getLogger(__name__)

ASSETS = {
    "db": "arm_budget.duckdb.xz",
    "parquet": "arm_budget-parquet.zip",
    "raw": "arm_budget-raw.tar.xz",
}
SUMS = "SHA256SUMS"
NOTES = "RELEASE_NOTES.md"
PARQUET_DIR = config.DATA_DIR / "parquet"


def repo() -> str:
    return os.environ.get("ARM_BUDGET_REPO", config.GITHUB_REPO)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=config.ROOT, check=True, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------------------
# packing
# ---------------------------------------------------------------------------

def snapshot_date(con: duckdb.DuckDBPyConnection) -> str:
    """Date of the data collection: the last report request."""
    return con.execute("SELECT max(fetched_at)::DATE::VARCHAR FROM meta_request").fetchone()[0]


def _export_parquet(con: duckdb.DuckDBPyConnection, out: Path) -> Path:
    """Every table and view as <name>.parquet (explicit COPY: EXPORT DATABASE mangles names)."""
    names = [r[0] for r in con.execute("""
        SELECT table_name FROM duckdb_tables() WHERE schema_name = 'main'
        UNION ALL
        SELECT view_name FROM duckdb_views() WHERE schema_name = 'main' AND NOT internal
        ORDER BY 1""").fetchall()]
    zpath = out / ASSETS["parquet"]
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            dst = Path(tmp) / f"{name}.parquet"
            con.execute(f"COPY (SELECT * FROM \"{name}\") TO '{dst}' (FORMAT parquet, COMPRESSION zstd)")
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_STORED) as z:  # parquet is already compressed
            for name in names:
                z.write(Path(tmp) / f"{name}.parquet", f"parquet/{name}.parquet")
            docs = config.ROOT / "docs"
            for src, name in [(docs / "data_dictionary.md", "data_dictionary.md")] + [
                    (docs / lang / "database.md", "database.md" if lang == "en" else f"database.{lang}.md")
                    for lang in ("en", "hy", "ru")]:
                if src.exists():
                    z.write(src, f"parquet/{name}")
    log.info("parquet: %d tables and views -> %s", len(names), zpath)
    return zpath


def _notes(con, tag: str, date: str, commit: str, out: Path) -> Path:
    def table(sql: str) -> str:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        fmt = lambda v: f"{v:,}" if isinstance(v, int) else ("" if v is None else str(v))
        return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
                         + ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows])

    coverage = table("""
        SELECT year, as_of_date AS "data as of", expenditure_lines AS "expenditure lines", revenue_lines AS "revenue lines",
               contracts, round(expenditure_plan_kamd / 1e6, 1) AS "expenditure plan, bn AMD",
               round(expenditure_actual_kamd / 1e6, 1) AS "executed, bn AMD"
        FROM v_summary ORDER BY year""")
    qc = table("SELECT check_name AS check, status, n_issues AS issues FROM qc_summary")
    assets = "\n".join(f"| `{n}` | {(out / n).stat().st_size / 1e6:.1f} MB |" for n in ASSETS.values())
    url = f"https://github.com/{repo()}"
    text = f"""Snapshot of the Armenian state budget execution data from the "Interactive budget" of the Ministry of Finance
(<{config.BASE_URL}/>), collected on {date}; names of the classifiers in Armenian, English and Russian.
The database was built with the code of commit [`{commit[:7]}`]({url}/commit/{commit}).

## Files

| file | size |
|---|---|
{assets}

* `{ASSETS["db"]}` — DuckDB database (description: [database.md]({url}/blob/{commit}/docs/en/database.md));
* `{ASSETS["parquet"]}` — all tables and views as Parquet + data dictionary;
* `{ASSETS["raw"]}` — raw data: report pages, Excel exports, probes, contract pages, PDF documents (`raw/`) and manifests (`catalog/`);
* `SHA256SUMS` — checksums.

## Usage

```bash
git clone {url}.git && cd {repo().split("/")[-1]}
make install
make download          # database -> data/arm_budget.duckdb (SHA256 verified)
make lab               # notebook with examples
```

Rebuild from the raw data without touching the website: `git checkout {tag}`, `make download-raw build`.
Manually: `curl -LO {url}/releases/download/{tag}/{ASSETS["db"]} && xz -d {ASSETS["db"]}`.

## Coverage

Amounts are in thousand AMD; the site keeps the latest three budget years. The latest year is incomplete
(execution up to the "data as of" date).

{coverage}

## Data quality checks

{qc}

Details: [data_quality.md]({url}/blob/{commit}/docs/en/data_quality.md).
"""
    path = out / NOTES
    path.write_text(text, encoding="utf-8")
    return path


def pack(tag: str | None = None) -> Path:
    """Pack the database, Parquet export and raw data into data/release/<tag>/."""
    if not config.DUCKDB_PATH.exists():
        raise SystemExit("database not found: run `make build` (or `make download`) first")
    con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    date = snapshot_date(con)
    tag = tag or f"data-{date}"
    out = config.RELEASE_DIR / tag
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    db_xz = out / ASSETS["db"]
    with open(config.DUCKDB_PATH, "rb") as src, lzma.open(db_xz, "wb", preset=6) as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    log.info("database -> %s", db_xz)

    _export_parquet(con, out)

    raw_xz = out / ASSETS["raw"]
    with tarfile.open(raw_xz, "w:xz", preset=6) as t:
        t.add(config.RAW_DIR, arcname="raw")
        t.add(config.CATALOG_DIR, arcname="catalog")
    log.info("raw data -> %s", raw_xz)

    (out / SUMS).write_text("".join(f"{sha256(out / n)}  {n}\n" for n in ASSETS.values()), encoding="utf-8")
    try:
        commit = _git("rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    _notes(con, tag, date, commit, out)
    con.close()
    log.info("release %s packed in %s", tag, out)
    return out


# ---------------------------------------------------------------------------
# publishing
# ---------------------------------------------------------------------------

def publish(tag: str | None = None) -> str:
    """Pack (if needed) and create the GitHub release with ``gh``.

    The working tree must be clean and HEAD pushed: the tag points to HEAD, so
    the release documents exactly the code the database was built with.
    """
    if _git("status", "--porcelain"):
        raise SystemExit("working tree is not clean: commit the changes before publishing a release")
    if not _git("branch", "-r", "--contains", "HEAD"):
        raise SystemExit("HEAD is not pushed: run `git push` before publishing a release")
    if not shutil.which("gh"):
        raise SystemExit("the GitHub CLI `gh` is required to publish a release")
    out = pack(tag)
    tag = out.name
    files = [str(out / n) for n in (*ASSETS.values(), SUMS)]
    date = tag.removeprefix("data-")
    subprocess.run(["gh", "release", "create", tag, *files, "--repo", repo(), "--target", _git("rev-parse", "HEAD"),
                    "--title", f"Data as of {date}", "--notes-file", str(out / NOTES)], check=True)
    log.info("published release %s to %s", tag, repo())
    return tag


# ---------------------------------------------------------------------------
# downloading
# ---------------------------------------------------------------------------

def asset_url(name: str, tag: str = "latest") -> str:
    base = f"https://github.com/{repo()}/releases"
    return f"{base}/latest/download/{name}" if tag == "latest" else f"{base}/download/{tag}/{name}"


def parse_sums(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[1].lstrip("*")] = parts[0].lower()
    return out


def _fetch(session: requests.Session, url: str, dst: Path, attempts: int = 30) -> None:
    """Download ``url`` to ``dst``; a dropped connection is resumed with an HTTP Range request.

    The partial file (``<dst>.part``) is kept between runs, so a later run continues it."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    for attempt in range(1, attempts + 1):
        have = tmp.stat().st_size if tmp.exists() else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with session.get(url, stream=True, timeout=(30, 120), headers=headers) as r:
                if r.status_code == 416:  # already complete
                    break
                r.raise_for_status()
                if have and r.status_code != 206:  # the server ignored the range: start again
                    have = 0
                with open(tmp, "ab" if have else "wb") as f:
                    f.writelines(r.iter_content(1 << 20))
            break
        except requests.RequestException as exc:
            if attempt == attempts:
                raise
            log.warning("%s: %s, resuming (attempt %d)", url.rsplit("/", 1)[-1], exc, attempt + 1)
            time.sleep(min(30, 3 * attempt))
    tmp.replace(dst)


def safe_members(t: tarfile.TarFile, prefix: str) -> list[tarfile.TarInfo]:
    """Members under ``prefix/`` that are plain files/dirs with safe relative paths."""
    out = []
    for m in t.getmembers():
        name = m.name
        if not (name == prefix or name.startswith(prefix + "/")):
            continue
        if name.startswith("/") or ".." in Path(name).parts or not (m.isfile() or m.isdir()):
            raise ValueError(f"unsafe archive member: {name}")
        out.append(m)
    return out


def download(tag: str = "latest", parts: tuple[str, ...] = ("db",), with_catalog: bool = False) -> None:
    """Download release assets, verify SHA256 and unpack them into data/."""
    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    cache = config.RELEASE_DIR / "download" / tag
    cache.mkdir(parents=True, exist_ok=True)
    sums = session.get(asset_url(SUMS, tag), timeout=60)
    sums.raise_for_status()
    expected = parse_sums(sums.text)
    for part in parts:
        name = ASSETS[part]
        path = cache / name
        if path.exists() and sha256(path) == expected.get(name):
            log.info("%s already downloaded", path)
        else:
            log.info("download %s", asset_url(name, tag))
            _fetch(session, asset_url(name, tag), path)
        digest = sha256(path)
        if digest != expected.get(name):
            path.unlink()
            raise SystemExit(f"checksum mismatch for {name}: got {digest}, expected {expected.get(name)}")
        if part == "db":
            tmp = config.DUCKDB_PATH.with_name(config.DUCKDB_PATH.name + ".download")
            with lzma.open(path) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            tmp.replace(config.DUCKDB_PATH)
            log.info("database -> %s", config.DUCKDB_PATH)
        elif part == "parquet":
            if PARQUET_DIR.exists():
                shutil.rmtree(PARQUET_DIR)
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    target = (config.DATA_DIR / info.filename).resolve()
                    if not str(target).startswith(str(config.DATA_DIR.resolve()) + os.sep):
                        raise ValueError(f"unsafe archive member: {info.filename}")
                z.extractall(config.DATA_DIR)
            log.info("parquet -> %s", PARQUET_DIR)
        elif part == "raw":
            with tarfile.open(path, "r:xz") as t:
                members = safe_members(t, "raw") + (safe_members(t, "catalog") if with_catalog else [])
                try:
                    t.extractall(config.DATA_DIR, members=members, filter="data")
                except TypeError:  # Python without tarfile extraction filters
                    t.extractall(config.DATA_DIR, members=members)
            log.info("raw data -> %s%s", config.RAW_DIR, " (+ catalog)" if with_catalog else "")
