"""Command line interface: ``python -m arm_budget <command>``."""

from __future__ import annotations

import argparse
import logging
import sys


def _years(s: str | None) -> tuple[int, ...] | None:
    return tuple(int(x) for x in s.split(",")) if s else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arm-budget", description="Armenian state budget (budget.minfin.am:82) -> DuckDB")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("catalog", help="start page, report forms per year (classifiers with codes), PDF documents -> data/catalog")

    f = sub.add_parser("fetch", help="report queries, Excel exports and code probes for every year -> data/raw/reports")
    f.add_argument("--years", help="comma separated calendar years (default: all on the site)")
    f.add_argument("--report", action="append", choices=["expenditure", "revenue", "deficit"])
    f.add_argument("--probes-only", action="store_true", help="only run missing code probes for the trees already on disk")

    c = sub.add_parser("contracts", help="contract pages of the expenditure lines -> data/raw/contracts")
    c.add_argument("--years", help="comma separated calendar years (default: all)")
    c.add_argument("--refresh-years", type=int, default=1,
                   help="re-download pages of the N most recent years when older than --max-age-hours (default 1)")
    c.add_argument("--max-age-hours", type=float, default=12)
    c.add_argument("--force", action="store_true", help="re-download every page")

    t = sub.add_parser("translations", help="write the Armenian strings without a translation to data/translations/pending")
    t.add_argument("--batch-size", type=int, default=150)
    t.add_argument("--merge", action="store_true", help="merge the filled files of data/translations/pending into the dictionaries")

    b = sub.add_parser("build", help="parse raw data and (re)build the DuckDB database")
    b.add_argument("--db", help="output path (default data/arm_budget.duckdb)")

    sub.add_parser("docs", help="regenerate docs/data_dictionary.md and docs/<lang>/inventory.md from the database")

    sub.add_parser("all", help="catalog + fetch + contracts + build + docs")

    r = sub.add_parser("release", help="pack the data snapshot and publish it as a GitHub release (needs gh)")
    r.add_argument("--tag", help="release tag (default data-<collection date>)")
    r.add_argument("--pack-only", action="store_true", help="only create the assets in data/release/<tag>")

    dl = sub.add_parser("download", help="download a data snapshot from GitHub releases into data/")
    dl.add_argument("--tag", default="latest", help="release tag (default: latest)")
    dl.add_argument("--part", action="append", choices=["db", "parquet", "raw"], help="what to download (default: db)")
    dl.add_argument("--with-catalog", action="store_true", help="with raw: also overwrite data/catalog from the snapshot")

    args = p.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if args.cmd in ("release", "download"):
        from . import release

        if args.cmd == "release":
            release.pack(args.tag) if args.pack_only else release.publish(args.tag)
        else:
            release.download(args.tag, tuple(args.part or ["db"]), args.with_catalog)
        return 0
    if args.cmd == "translations":
        from . import translations

        translations.merge_pending() if args.merge else translations.write_pending(args.batch_size)
        return 0

    from . import fetch

    if args.cmd in ("catalog", "all"):
        fetch.catalog()
    if args.cmd in ("fetch", "all"):
        fetch.fetch(_years(getattr(args, "years", None)), tuple(args.report) if getattr(args, "report", None) else None,
                    getattr(args, "probes_only", False))
    if args.cmd in ("contracts", "all"):
        fetch.fetch_contracts(_years(getattr(args, "years", None)), getattr(args, "refresh_years", 1), getattr(args, "force", False),
                              getattr(args, "max_age_hours", 12))
    if args.cmd in ("build", "all"):
        from . import build

        build.build(getattr(args, "db", None))
    if args.cmd in ("docs", "all"):
        from . import docs

        docs.write_data_dictionary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
