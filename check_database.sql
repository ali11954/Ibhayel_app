-- =====================================================
-- سكريبت فحص سريع: ما الذي ينقص من القاعدة القديمة؟
-- شغّل هذا أولاً لمعرفة ما يحتاج تحديث
-- =====================================================

-- === فحص الأعمدة المفقودة في users ===
SELECT 'users' AS table_name, 
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'employee_id') 
            THEN 'employee_id EXISTS' ELSE 'employee_id MISSING' END AS status
UNION ALL
SELECT 'users',
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'allowed_pages') 
            THEN 'allowed_pages EXISTS' ELSE 'allowed_pages MISSING' END;

-- === فحص الأعمدة المفقودة في employees ===
SELECT 'employees' AS table_name, column_name,
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'employees' AND column_name = c.column_name) 
            THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (VALUES 
    ('supervisor_id'), ('basic_salary'), ('clothing_allowance'), 
    ('health_card_allowance'), ('monthly_insurance'), ('contractor_tax'),
    ('contractor_zakat'), ('daily_allowance'), ('total_salary'),
    ('allowances_updated_at'), ('region_id'), ('user_id'), ('worker_type')
) AS c(column_name);

-- === فحص الأعمدة المفقودة في financial_transactions ===
SELECT 'financial_transactions' AS table_name, column_name,
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'financial_transactions' AND column_name = c.column_name) 
            THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (VALUES 
    ('payment_method'), ('supplier_id'), ('monthly_installment'),
    ('settled_amount'), ('journal_entry_id')
) AS c(column_name);

-- === فحص الجداول المفقودة ===
SELECT table_name,
       CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = t.table_name) 
            THEN 'EXISTS' ELSE 'MISSING' END AS status
FROM (VALUES 
    ('accounts'), ('journal_entries'), ('journal_entry_details'),
    ('account_balances'), ('fiscal_years'), ('trial_balances'),
    ('financial_periods'), ('leave_types'), ('leave_balances'),
    ('leave_requests'), ('suppliers'), ('expense_categories'),
    ('supplier_invoices'), ('supplier_invoice_payments'),
    ('company_payments'), ('system_settings'), ('allowance_settings'),
    ('area_evaluations'), ('area_evaluation_criteria'),
    ('labor_monthly_costs'), ('contractor_annual_costs'),
    ('contracts'), ('invoices'), ('meal_deductions'),
    ('meal_deduction_settings'), ('work_plans'), ('work_plan_tasks'),
    ('attendance_preparations'), ('attendance_preparation_details'),
    ('attendance_period_transfers'), ('attendance_period_transfer_details')
) AS t(table_name);

-- === فحص الحسابات المحاسبية ===
SELECT 'accounts_seed' AS check_name,
       CASE WHEN COUNT(*) >= 20 THEN 'SEDED (' || COUNT(*) || ' accounts)' ELSE 'NEEDS SEEDING (' || COUNT(*) || ' accounts)' END AS status
FROM accounts;

-- === فحص أنواع الإجازات ===
SELECT 'leave_types_seed' AS check_name,
       CASE WHEN COUNT(*) >= 4 THEN 'SEDED (' || COUNT(*) || ' types)' ELSE 'NEEDS SEEDING (' || COUNT(*) || ' types)' END AS status
FROM leave_types;

-- === ملخص ===
SELECT '========================================' AS separator;
SELECT 'إجمالي الجداول في القاعدة: ' || COUNT(*) AS summary FROM information_schema.tables WHERE table_schema = 'public';
SELECT 'إجمالي الحسابات المحاسبية: ' || COUNT(*) AS summary FROM accounts;
SELECT 'إجمالي أنواع الإجازات: ' || COUNT(*) AS summary FROM leave_types;
SELECT 'إجمالي المستخدمين: ' || COUNT(*) AS summary FROM users;
SELECT 'إجمالي الموظفين: ' || COUNT(*) AS summary FROM employees;
