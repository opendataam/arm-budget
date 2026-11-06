-- Views: facts with the names of all classifiers in three languages, long (period) layouts, summaries.

CREATE VIEW v_expenditure AS
SELECT
    f.year, f.line_no,
    f.func_section_code, fs.name_hy AS func_section_hy, fs.name_en AS func_section_en, fs.name_ru AS func_section_ru,
    f.func_group_code,   fg.name_hy AS func_group_hy,   fg.name_en AS func_group_en,   fg.name_ru AS func_group_ru,
    f.func_class_code,   fc.name_hy AS func_class_hy,   fc.name_en AS func_class_en,   fc.name_ru AS func_class_ru,
    f.program_code,      p.name_hy  AS program_hy,      p.name_en  AS program_en,      p.name_ru  AS program_ru,
    f.department_code,   d.name_hy  AS department_hy,   d.name_en  AS department_en,   d.name_ru  AS department_ru,
    e.class_code AS economic_class_code, el1.name_en AS economic_class_en,
    e.category_code AS economic_category_code, el2.name_en AS economic_category_en,
    e.group_code AS economic_group_code, el3.name_en AS economic_group_en,
    f.economic_code,     e.name_hy  AS economic_hy,     e.name_en  AS economic_en,     e.name_ru  AS economic_ru,
    f.contract_line_id,
    f.q1_plan_kamd, f.q1_actual_kamd, f.h1_plan_kamd, f.h1_actual_kamd,
    f.m9_plan_kamd, f.m9_actual_kamd, f.year_plan_kamd, f.year_actual_kamd,
    round(100 * f.year_actual_kamd / nullif(f.year_plan_kamd, 0), 1) AS year_execution_pct
FROM fact_expenditure f
LEFT JOIN dim_functional fs ON fs.code = f.func_section_code
LEFT JOIN dim_functional fg ON fg.code = f.func_group_code
LEFT JOIN dim_functional fc ON fc.code = f.func_class_code
LEFT JOIN dim_program p ON p.code = f.program_code
LEFT JOIN dim_department d ON d.code = f.department_code
LEFT JOIN dim_economic e ON e.code = f.economic_code
LEFT JOIN dim_economic_level el1 ON el1.code = e.class_code
LEFT JOIN dim_economic_level el2 ON el2.code = e.category_code
LEFT JOIN dim_economic_level el3 ON el3.code = e.group_code;
COMMENT ON VIEW v_expenditure IS 'fact_expenditure with the names of all classifiers in hy / en / ru and the upper levels of the economic classification. Thousand AMD.';

CREATE VIEW v_expenditure_long AS
SELECT f.year, f.line_no, f.func_class_code, f.program_code, f.department_code, f.economic_code,
       p.period, p.months,
       CASE p.period WHEN 'q1' THEN f.q1_plan_kamd WHEN 'h1' THEN f.h1_plan_kamd WHEN 'm9' THEN f.m9_plan_kamd ELSE f.year_plan_kamd END AS plan_kamd,
       CASE p.period WHEN 'q1' THEN f.q1_actual_kamd WHEN 'h1' THEN f.h1_actual_kamd WHEN 'm9' THEN f.m9_actual_kamd ELSE f.year_actual_kamd END AS actual_kamd
FROM fact_expenditure f CROSS JOIN dim_period p;
COMMENT ON VIEW v_expenditure_long IS 'fact_expenditure with one row per period (q1, h1, m9, year): cumulative plan and executed amount, thousand AMD.';

CREATE VIEW v_revenue AS
SELECT
    f.year, f.revenue_type, t.name_hy AS revenue_type_hy, t.name_en AS revenue_type_en, t.name_ru AS revenue_type_ru,
    f.line_no, f.line_kind,
    f.rev_section_code, s.name_hy AS rev_section_hy, s.name_en AS rev_section_en, s.name_ru AS rev_section_ru,
    f.rev_group_code,   g.name_hy AS rev_group_hy,   g.name_en AS rev_group_en,   g.name_ru AS rev_group_ru,
    f.department_code,  d.name_hy AS department_hy,  d.name_en AS department_en,  d.name_ru AS department_ru,
    f.rev_account_code, a.name_hy AS rev_account_hy, a.name_en AS rev_account_en, a.name_ru AS rev_account_ru,
    f.q1_plan_kamd, f.q1_actual_kamd, f.h1_plan_kamd, f.h1_actual_kamd,
    f.m9_plan_kamd, f.m9_actual_kamd, f.year_plan_kamd, f.year_actual_kamd
FROM fact_revenue f
LEFT JOIN dim_revenue_type t ON t.revenue_type = f.revenue_type
LEFT JOIN dim_revenue_section s ON s.code = f.rev_section_code
LEFT JOIN dim_revenue_group g ON g.code = f.rev_group_code
LEFT JOIN dim_department d ON d.code = f.department_code
LEFT JOIN dim_revenue_account a ON a.code = f.rev_account_code;
COMMENT ON VIEW v_revenue IS 'fact_revenue with the names of all classifiers in hy / en / ru. Thousand AMD.';

CREATE VIEW v_revenue_long AS
SELECT f.year, f.revenue_type, f.line_no, f.line_kind, f.rev_section_code, f.rev_group_code, f.department_code, f.rev_account_code,
       p.period, p.months,
       CASE p.period WHEN 'q1' THEN f.q1_plan_kamd WHEN 'h1' THEN f.h1_plan_kamd WHEN 'm9' THEN f.m9_plan_kamd ELSE f.year_plan_kamd END AS plan_kamd,
       CASE p.period WHEN 'q1' THEN f.q1_actual_kamd WHEN 'h1' THEN f.h1_actual_kamd WHEN 'm9' THEN f.m9_actual_kamd ELSE f.year_actual_kamd END AS actual_kamd
FROM fact_revenue f CROSS JOIN dim_period p;
COMMENT ON VIEW v_revenue_long IS 'fact_revenue with one row per period (q1, h1, m9, year), thousand AMD.';

CREATE VIEW v_deficit AS
SELECT year, line_no, item_code, row_kind, level, parent_line_no, label_hy, label_en, label_ru, note_hy, in_totals_view,
       q1_plan_kamd, q1_actual_kamd, h1_plan_kamd, h1_actual_kamd, m9_plan_kamd, m9_actual_kamd, year_plan_kamd, year_actual_kamd
FROM fact_deficit
WHERE row_kind <> 'note';
COMMENT ON VIEW v_deficit IS 'Deficit financing lines without the separator rows. Sum only lines of one row_kind under one parent; detail lines are breakdowns.';

CREATE VIEW v_contract AS
SELECT c.year, c.contract_line_id, c.seq, c.partner_hy, c.partner_en, c.partner_ru, c.start_date, c.end_date,
       c.amount_kamd, c.paid_kamd, c.n_files,
       f.department_code, d.name_en AS department_en, f.program_code, p.name_en AS program_en,
       f.economic_code, e.name_en AS economic_en, f.func_class_code,
       f.year_plan_kamd AS line_year_plan_kamd, f.year_actual_kamd AS line_year_actual_kamd
FROM fact_contract c
LEFT JOIN fact_expenditure f ON f.year = c.year AND f.contract_line_id = c.contract_line_id
LEFT JOIN dim_department d ON d.code = f.department_code
LEFT JOIN dim_program p ON p.code = f.program_code
LEFT JOIN dim_economic e ON e.code = f.economic_code;
COMMENT ON VIEW v_contract IS 'Contracts with the classification of the expenditure line they are paid from.';

CREATE VIEW v_summary AS
SELECT y.year, y.as_of_date, y.is_complete,
       (SELECT sum(year_plan_kamd) FROM fact_expenditure f WHERE f.year = y.year) AS expenditure_plan_kamd,
       (SELECT sum(year_actual_kamd) FROM fact_expenditure f WHERE f.year = y.year) AS expenditure_actual_kamd,
       (SELECT sum(year_plan_kamd) FROM fact_revenue f WHERE f.year = y.year) AS revenue_plan_kamd,
       (SELECT sum(year_actual_kamd) FROM fact_revenue f WHERE f.year = y.year) AS revenue_actual_kamd,
       (SELECT year_plan_kamd FROM fact_deficit f WHERE f.year = y.year AND row_kind = 'total') AS deficit_plan_kamd,
       (SELECT year_actual_kamd FROM fact_deficit f WHERE f.year = y.year AND row_kind = 'total') AS deficit_actual_kamd,
       (SELECT count(*) FROM fact_expenditure f WHERE f.year = y.year) AS expenditure_lines,
       (SELECT count(*) FROM fact_revenue f WHERE f.year = y.year) AS revenue_lines,
       (SELECT count(*) FROM fact_contract c WHERE c.year = y.year) AS contracts
FROM meta_year y
ORDER BY y.year;
COMMENT ON VIEW v_summary IS 'Totals by year: annual plan and execution of expenditures, revenues and the deficit, thousand AMD.';

CREATE VIEW v_expenditure_by_department AS
SELECT f.year, f.department_code, d.name_hy AS department_hy, d.name_en AS department_en, d.name_ru AS department_ru,
       sum(f.year_plan_kamd) AS year_plan_kamd, sum(f.year_actual_kamd) AS year_actual_kamd,
       round(100 * sum(f.year_actual_kamd) / nullif(sum(f.year_plan_kamd), 0), 1) AS year_execution_pct
FROM fact_expenditure f LEFT JOIN dim_department d ON d.code = f.department_code
GROUP BY ALL;
COMMENT ON VIEW v_expenditure_by_department IS 'Annual plan and execution of expenditures by department and year, thousand AMD.';

CREATE VIEW v_expenditure_by_function AS
SELECT f.year, f.func_section_code, s.name_hy AS func_section_hy, s.name_en AS func_section_en, s.name_ru AS func_section_ru,
       sum(f.year_plan_kamd) AS year_plan_kamd, sum(f.year_actual_kamd) AS year_actual_kamd,
       round(100 * sum(f.year_actual_kamd) / nullif(sum(f.year_plan_kamd), 0), 1) AS year_execution_pct
FROM fact_expenditure f LEFT JOIN dim_functional s ON s.code = f.func_section_code
GROUP BY ALL;
COMMENT ON VIEW v_expenditure_by_function IS 'Annual plan and execution of expenditures by functional section and year, thousand AMD.';
