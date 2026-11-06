-- Data quality checks. Every check is a table qc_<name> (rows = issues) and a row in qc_summary.
-- status: ok (no issues), warn (issues that need attention), info (expected differences, for reference).

-- 1. Codes that could not be resolved for fact rows.
CREATE TABLE qc_unresolved_code AS
SELECT n.request_id, n.recid, n.year, n.level, n.dim, n.label_hy
FROM stg_report_node n JOIN meta_request q USING (request_id)
WHERE n.level >= 0 AND n.code IS NULL AND (q.name = 'expenditure' OR q.revenue_type IN (1, 2, 3));
COMMENT ON TABLE qc_unresolved_code IS 'Tree nodes of the fact requests whose classifier code could not be resolved (neither by name nor by a probe).';

-- 2. Facts add up to the grand total of every tree.
CREATE TABLE qc_tree_total AS
WITH t AS (
    SELECT request_id, max(year_plan_kamd) FILTER (WHERE level = -1) AS total_plan,
           max(year_actual_kamd) FILTER (WHERE level = -1) AS total_actual
    FROM stg_report_node GROUP BY request_id),
f AS (
    SELECT request_id, sum(year_plan_kamd) AS facts_plan, sum(year_actual_kamd) AS facts_actual FROM fact_expenditure GROUP BY ALL
    UNION ALL
    SELECT request_id, sum(year_plan_kamd), sum(year_actual_kamd) FROM fact_revenue GROUP BY ALL)
SELECT t.request_id, f.facts_plan, t.total_plan, f.facts_actual, t.total_actual
FROM t JOIN f USING (request_id)
WHERE abs(f.facts_plan - t.total_plan) > 1 OR abs(f.facts_actual - t.total_actual) > 1;
COMMENT ON TABLE qc_tree_total IS 'Requests whose fact rows do not add up to the grand total of the source (annual plan or execution, tolerance 1 thousand AMD).';

-- 2a. Revenue plan not distributed to the accounts (informative).
CREATE TABLE qc_revenue_unallocated AS
WITH t AS (
    SELECT year, revenue_type, sum(year_plan_kamd) FILTER (WHERE line_kind = 'unallocated') AS unallocated_plan_kamd,
           sum(year_plan_kamd) AS total_plan_kamd
    FROM fact_revenue GROUP BY year, revenue_type)
SELECT *, round(100 * unallocated_plan_kamd / nullif(total_plan_kamd, 0), 1) AS unallocated_pct
FROM t WHERE unallocated_plan_kamd IS NOT NULL ORDER BY year, revenue_type;
COMMENT ON TABLE qc_revenue_unallocated IS 'Part of the annual revenue plan set for the revenue type as a whole (fact_revenue.line_kind = unallocated).';

-- 3. Every subtotal equals the sum of its children.
CREATE TABLE qc_tree_subtotal AS
SELECT p.request_id, p.recid, p.level, p.label_hy, p.year_plan_kamd, sum(c.year_plan_kamd) AS children_plan,
       p.year_actual_kamd, sum(c.year_actual_kamd) AS children_actual
FROM stg_report_node p JOIN stg_report_node c ON c.request_id = p.request_id AND c.parent_recid = p.recid
WHERE p.level >= 0
GROUP BY ALL
HAVING abs(p.year_plan_kamd - sum(c.year_plan_kamd)) > 0.01 OR abs(p.year_actual_kamd - sum(c.year_actual_kamd)) > 0.01;
COMMENT ON TABLE qc_tree_subtotal IS 'Subtotal rows that differ from the sum of their children.';

-- 4. Revenue types add up to "all revenues".
CREATE TABLE qc_revenue_types AS
WITH t AS (
    SELECT q.year, q.revenue_type, n.year_plan_kamd AS plan, n.year_actual_kamd AS actual
    FROM stg_report_node n JOIN meta_request q USING (request_id)
    WHERE q.report = 'revenue' AND n.level = -1)
SELECT year,
       sum(plan) FILTER (WHERE revenue_type > 0) AS types_plan, max(plan) FILTER (WHERE revenue_type = 0) AS all_plan,
       sum(actual) FILTER (WHERE revenue_type > 0) AS types_actual, max(actual) FILTER (WHERE revenue_type = 0) AS all_actual
FROM t GROUP BY year
HAVING abs(types_plan - all_plan) > greatest(1, 0.0001 * abs(all_plan)) OR abs(types_actual - all_actual) > 1;
COMMENT ON TABLE qc_revenue_types IS 'Years where taxes + grants + other revenues differ from all revenues (SITE_EBUDG 1+2+3 vs 0); plan tolerance 0.01 %.';

-- 5. Totals of the start page = annual plans of the latest year.
CREATE TABLE qc_site_total AS
SELECT s.report, s.year, s.total_kamd,
       CASE s.report
           WHEN 'expenditure' THEN (SELECT sum(year_plan_kamd) FROM fact_expenditure f WHERE f.year = s.year)
           WHEN 'revenue' THEN (SELECT sum(year_plan_kamd) FROM fact_revenue f WHERE f.year = s.year)
           ELSE (SELECT year_plan_kamd FROM fact_deficit f WHERE f.year = s.year AND row_kind = 'total') END AS database_kamd
FROM meta_site_total s;
DELETE FROM qc_site_total WHERE abs(total_kamd - database_kamd) <= 1;
COMMENT ON TABLE qc_site_total IS 'Reports whose total on the start page differs from the annual plan in the database.';

-- 6. Budget balance: expenditure plan - revenue plan = deficit plan.
CREATE TABLE qc_balance AS
SELECT year, expenditure_plan_kamd - revenue_plan_kamd AS plan_gap_kamd, deficit_plan_kamd,
       expenditure_actual_kamd - revenue_actual_kamd AS actual_gap_kamd, deficit_actual_kamd
FROM v_summary
WHERE abs(expenditure_plan_kamd - revenue_plan_kamd - deficit_plan_kamd) > 0.001 * deficit_plan_kamd;
COMMENT ON TABLE qc_balance IS 'Years where the annual expenditure plan minus the revenue plan differs from the planned deficit by more than 0.1 % (informative: the deficit statement can show another edition of the plan).';

-- 7. Expenditure lines with contracts.
CREATE TABLE qc_contract_link AS
SELECT 'line without contract page' AS issue, f.year, f.contract_line_id
FROM fact_expenditure f
WHERE f.contract_line_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM fact_contract c WHERE c.year = f.year AND c.contract_line_id = f.contract_line_id)
UNION ALL
SELECT 'contract without expenditure line', c.year, c.contract_line_id
FROM (SELECT DISTINCT year, contract_line_id FROM fact_contract) c
WHERE NOT EXISTS (SELECT 1 FROM fact_expenditure f WHERE f.year = c.year AND f.contract_line_id = c.contract_line_id);
COMMENT ON TABLE qc_contract_link IS 'Expenditure lines marked as having contracts without contract data, and contract pages not linked to an expenditure line.';

-- 8. Paid under contracts vs executed on the line (informative: lines also pay without contracts).
CREATE TABLE qc_contract_paid AS
SELECT f.year, f.contract_line_id, f.year_actual_kamd, sum(c.paid_kamd) AS paid_kamd
FROM fact_expenditure f JOIN fact_contract c ON c.year = f.year AND c.contract_line_id = f.contract_line_id
GROUP BY ALL
HAVING sum(c.paid_kamd) > f.year_actual_kamd + 1;
COMMENT ON TABLE qc_contract_paid IS 'Expenditure lines where the payments listed for contracts exceed the executed amount of the line (by more than 1 thousand AMD).';

-- 9. Names without a translation.
CREATE TABLE qc_missing_translation AS
SELECT DISTINCT context, hy FROM (
    SELECT 'functional' AS context, name_hy AS hy, name_en AS en, name_ru AS ru FROM dim_functional
    UNION ALL SELECT 'program', name_hy, name_en, name_ru FROM dim_program
    UNION ALL SELECT 'department', name_hy, name_en, name_ru FROM dim_department
    UNION ALL SELECT 'economic', name_hy, name_en, name_ru FROM dim_economic
    UNION ALL SELECT 'revenue', name_hy, name_en, name_ru FROM dim_revenue_section
    UNION ALL SELECT 'revenue', name_hy, name_en, name_ru FROM dim_revenue_group
    UNION ALL SELECT 'revenue', name_hy, name_en, name_ru FROM dim_revenue_account
    UNION ALL SELECT 'deficit', label_hy, label_en, label_ru FROM fact_deficit WHERE row_kind <> 'note'
    UNION ALL SELECT 'labels', hy, en, ru FROM meta_label
) WHERE hy IS NOT NULL AND hy <> '' AND (en IS NULL OR ru IS NULL)
ORDER BY context, hy;
COMMENT ON TABLE qc_missing_translation IS 'Armenian names without an English or Russian translation (python -m arm_budget translations writes them to data/translations/pending).';

-- 10. Names of the same code that differ between years.
CREATE TABLE qc_renamed_code AS
SELECT report, dim, code, count(DISTINCT name_hy) AS n_names, string_agg(DISTINCT year::VARCHAR, ',' ORDER BY year::VARCHAR) AS years
FROM dim_name GROUP BY report, dim, code HAVING count(DISTINCT name_hy) > 1;
COMMENT ON TABLE qc_renamed_code IS 'Classifier codes whose name changed between years (informative; dim_* keep the latest name, dim_name all of them).';

CREATE TABLE qc_summary AS
SELECT * FROM (VALUES
    ('unresolved_code', CASE WHEN (SELECT count(*) FROM qc_unresolved_code) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_unresolved_code), 'tree nodes of fact requests without a classifier code'),
    ('tree_total', CASE WHEN (SELECT count(*) FROM qc_tree_total) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_tree_total), 'requests whose fact rows do not add up to the grand total'),
    ('revenue_unallocated', 'info', (SELECT count(*) FROM qc_revenue_unallocated),
        'year x revenue type with plan not distributed to accounts'),
    ('tree_subtotal', CASE WHEN (SELECT count(*) FROM qc_tree_subtotal) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_tree_subtotal), 'subtotals that differ from the sum of their children'),
    ('revenue_types', CASE WHEN (SELECT count(*) FROM qc_revenue_types) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_revenue_types), 'years where revenue types do not add up to all revenues'),
    ('site_total', CASE WHEN (SELECT count(*) FROM qc_site_total) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_site_total), 'start page totals that differ from the database'),
    ('balance', 'info', (SELECT count(*) FROM qc_balance), 'years where expenditure plan - revenue plan <> deficit plan (by more than 0.1 %)'),
    ('contract_link', CASE WHEN (SELECT count(*) FROM qc_contract_link) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_contract_link), 'contract lines without contracts / contracts without a line'),
    ('contract_paid', 'info', (SELECT count(*) FROM qc_contract_paid), 'lines where contract payments exceed the executed amount'),
    ('missing_translation', CASE WHEN (SELECT count(*) FROM qc_missing_translation) = 0 THEN 'ok' ELSE 'warn' END,
        (SELECT count(*) FROM qc_missing_translation), 'names without an en or ru translation'),
    ('renamed_code', 'info', (SELECT count(*) FROM qc_renamed_code), 'codes whose name changed between years')
) AS t(check_name, status, n_issues, description);
COMMENT ON TABLE qc_summary IS 'Summary of the data quality checks (qc_* tables).';
