"""Checks of the built database (skipped if data/arm_budget.duckdb does not exist)."""

import duckdb
import pytest

from arm_budget import config

pytestmark = pytest.mark.skipif(not config.DUCKDB_PATH.exists(), reason="database not built (make build)")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    yield c
    c.close()


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def test_every_year_has_all_reports(con):
    years = [r[0] for r in con.execute("SELECT year FROM meta_year").fetchall()]
    assert len(years) >= 3
    for table in ("fact_expenditure", "fact_revenue", "fact_deficit"):
        got = {r[0] for r in con.execute(f"SELECT DISTINCT year FROM {table}").fetchall()}
        assert got == set(years), table


def test_codes_resolved(con):
    # a few revenue labels have no counterpart in any classifier list of the site (docs/en/data_quality.md)
    assert one(con, "SELECT count(*) FROM qc_unresolved_code") <= 20
    assert one(con, "SELECT count(*) FROM qc_unresolved_code WHERE request_id LIKE 'expenditure%'") == 0
    for col in ("func_class_code", "program_code", "department_code", "economic_code"):
        assert one(con, f"SELECT count(*) FROM fact_expenditure WHERE {col} IS NULL") == 0, col
    n_null = one(con, """SELECT count(*) FROM fact_revenue
                         WHERE rev_section_code IS NULL OR rev_group_code IS NULL OR department_code IS NULL OR rev_account_code IS NULL""")
    assert n_null <= 0.01 * one(con, "SELECT count(*) FROM fact_revenue")


def test_codes_exist_in_dimensions(con):
    assert one(con, "SELECT count(*) FROM fact_expenditure f ANTI JOIN dim_program d ON d.code = f.program_code") == 0
    assert one(con, "SELECT count(*) FROM fact_expenditure f ANTI JOIN dim_functional d ON d.code = f.func_class_code") == 0
    assert one(con, """SELECT count(*) FROM fact_revenue f ANTI JOIN dim_revenue_account d ON d.code = f.rev_account_code
                       WHERE f.rev_account_code IS NOT NULL""") == 0


def test_functional_hierarchy(con):
    assert one(con, """SELECT count(*) FROM fact_expenditure
                       WHERE NOT starts_with(func_class_code, func_group_code) OR NOT starts_with(func_group_code, func_section_code)""") == 0


def test_totals_add_up(con):
    assert one(con, "SELECT count(*) FROM qc_tree_total") == 0
    assert one(con, "SELECT count(*) FROM qc_revenue_types") == 0
    assert one(con, "SELECT count(*) FROM qc_site_total") == 0


def test_names_in_three_languages(con):
    for table in ("dim_functional", "dim_program", "dim_department", "dim_economic", "dim_revenue_account"):
        # codes listed without a name and without data have no name in any language
        n, en, ru = con.execute(f"SELECT count(*), count(name_en), count(name_ru) FROM {table} WHERE coalesce(name_hy, '') <> ''").fetchone()
        assert n > 0 and en == n and ru == n, table


def test_contracts_linked(con):
    assert one(con, "SELECT count(*) FROM fact_contract") > 0
    assert one(con, "SELECT count(*) FROM qc_contract_link") == 0
