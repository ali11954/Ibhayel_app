-- =====================================================
-- م腳يغرات قاعدة البيانات: التحديث من النظام القديم إلى الجديد
-- الحفاظ على جميع البيانات الموجودة
-- قاعدة البيانات: Supabase PostgreSQL
-- =====================================================

-- =====================================================
-- الجزء 1: إضافة أعمدة جديدة للجداول الموجودة
-- =====================================================

-- === users ===
ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_pages TEXT;

-- === employees ===
ALTER TABLE employees ADD COLUMN IF NOT EXISTS supervisor_id INTEGER REFERENCES employees(id) ON DELETE SET NULL;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS basic_salary FLOAT DEFAULT 2000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS clothing_allowance FLOAT DEFAULT 24480;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS health_card_allowance FLOAT DEFAULT 15000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS monthly_insurance FLOAT DEFAULT 10800;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS contractor_tax FLOAT DEFAULT 500000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS contractor_zakat FLOAT DEFAULT 75000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS daily_allowance FLOAT DEFAULT 500;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS total_salary FLOAT DEFAULT 60000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS allowances_updated_at TIMESTAMP DEFAULT NOW();
ALTER TABLE employees ADD COLUMN IF NOT EXISTS region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS worker_type VARCHAR(20) DEFAULT 'permanent';

-- === financial_transactions ===
ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) DEFAULT 'cash';
ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL;
ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS monthly_installment FLOAT DEFAULT 0;
ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS settled_amount FLOAT DEFAULT 0;
ALTER TABLE financial_transactions ADD COLUMN IF NOT EXISTS journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL;

-- === salaries (إضافة أعمدة جديدة) ===
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS cafeteria_supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS restaurant_supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS cafeteria_paid_to_supplier BOOLEAN DEFAULT FALSE;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS restaurant_paid_to_supplier BOOLEAN DEFAULT FALSE;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS contractor_profit NUMERIC(12,2) DEFAULT 0;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS is_calculated BOOLEAN DEFAULT FALSE;
ALTER TABLE salaries ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMP;

-- === companies ===
ALTER TABLE companies ADD COLUMN IF NOT EXISTS receivable_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL;

-- === suppliers ===
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS payable_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL;
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS name_ar VARCHAR(200) DEFAULT '';
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS supplier_type VARCHAR(50) DEFAULT 'general';

-- === evaluation_criteria ===
ALTER TABLE evaluation_criteria ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL;

-- === evaluations ===
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL;
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL;

-- === invoices ===
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL;

-- === attendances ===
ALTER TABLE attendances ADD COLUMN IF NOT EXISTS sick_leave BOOLEAN DEFAULT FALSE;
ALTER TABLE attendances ADD COLUMN IF NOT EXISTS sick_leave_days INTEGER DEFAULT 0;
ALTER TABLE attendances ADD COLUMN IF NOT EXISTS annual_leave_days INTEGER DEFAULT 0;


-- =====================================================
-- الجزء 2: إنشاء الجداول الجديدة
-- =====================================================

-- === الجداول المحاسبية ===

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    nature VARCHAR(10) NOT NULL,
    parent_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    level INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    opening_balance FLOAT DEFAULT 0,
    opening_balance_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id SERIAL PRIMARY KEY,
    entry_number VARCHAR(50) NOT NULL UNIQUE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    description VARCHAR(500) NOT NULL,
    reference_type VARCHAR(50),
    reference_id INTEGER,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_posted BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journal_entry_details (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    debit FLOAT DEFAULT 0,
    credit FLOAT DEFAULT 0,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account_balances (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    period INTEGER NOT NULL,
    opening_balance FLOAT DEFAULT 0,
    debit FLOAT DEFAULT 0,
    credit FLOAT DEFAULT 0,
    closing_balance FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(account_id, fiscal_year, period)
);

CREATE TABLE IF NOT EXISTS fiscal_years (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trial_balances (
    id SERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    opening_balance FLOAT DEFAULT 0,
    debit FLOAT DEFAULT 0,
    credit FLOAT DEFAULT 0,
    closing_balance FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === الفترات المالية ===

CREATE TABLE IF NOT EXISTS financial_periods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    period_type VARCHAR(20) NOT NULL DEFAULT 'monthly',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    fiscal_year_id INTEGER REFERENCES fiscal_years(id) ON DELETE SET NULL,
    closed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    closed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(period_type, start_date, end_date)
);

-- === الإجازات ===

CREATE TABLE IF NOT EXISTS leave_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    days_per_year INTEGER DEFAULT 30,
    is_paid BOOLEAN DEFAULT TRUE,
    max_consecutive_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leave_balances (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    total_days FLOAT DEFAULT 0,
    used_days FLOAT DEFAULT 0,
    remaining_days FLOAT DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(employee_id, leave_type_id, year)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id) ON DELETE RESTRICT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days FLOAT NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    is_paid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === الموردين والفواتير ===

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL DEFAULT '',
    contact_person VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    address VARCHAR(300),
    tax_number VARCHAR(50),
    bank_name VARCHAR(100),
    bank_account VARCHAR(100),
    notes TEXT,
    supplier_type VARCHAR(50) DEFAULT 'general',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    payable_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS expense_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    parent_id INTEGER REFERENCES expense_categories(id) ON DELETE SET NULL,
    account_code VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplier_invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    category_id INTEGER REFERENCES expense_categories(id) ON DELETE SET NULL,
    amount FLOAT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    paid_amount FLOAT DEFAULT 0,
    remaining_amount FLOAT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(50),
    reference_number VARCHAR(100),
    description TEXT,
    notes TEXT,
    document_path VARCHAR(500),
    is_posted_to_accounts BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS supplier_invoice_payments (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES supplier_invoices(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(50),
    reference_number VARCHAR(100),
    notes TEXT,
    is_posted_to_accounts BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === الدفعات ===

CREATE TABLE IF NOT EXISTS company_payments (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    amount FLOAT NOT NULL,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(50),
    reference_number VARCHAR(100),
    notes TEXT,
    is_posted_to_accounts BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- === الإعدادات ===

CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_name VARCHAR(200) NOT NULL,
    setting_name_ar VARCHAR(200) NOT NULL,
    value FLOAT DEFAULT 0,
    value_type VARCHAR(20) DEFAULT 'monthly',
    is_percentage BOOLEAN DEFAULT FALSE,
    percentage_of VARCHAR(50),
    account_code VARCHAR(20),
    account_name VARCHAR(200),
    account_type VARCHAR(20) DEFAULT 'expense',
    is_active BOOLEAN DEFAULT TRUE,
    is_required BOOLEAN DEFAULT FALSE,
    category VARCHAR(50) DEFAULT 'allowance',
    display_order INTEGER DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS allowance_settings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    allowance_type VARCHAR(50) DEFAULT 'fixed',
    value FLOAT DEFAULT 0,
    based_on VARCHAR(50) DEFAULT 'basic_salary',
    calculation_method VARCHAR(50) DEFAULT 'add',
    paid_to VARCHAR(50) DEFAULT 'employee',
    applies_to VARCHAR(50) DEFAULT 'all',
    account_code VARCHAR(20),
    account_name VARCHAR(200),
    account_type VARCHAR(20) DEFAULT 'expense',
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- === التقييمات ===

CREATE TABLE IF NOT EXISTS area_evaluations (
    id SERIAL PRIMARY KEY,
    evaluation_type VARCHAR(50) NOT NULL,
    region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    evaluation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    evaluator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    overall_score FLOAT DEFAULT 0,
    comments TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    is_active BOOLEAN DEFAULT TRUE,
    criteria_scores TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS area_evaluation_criteria (
    id SERIAL PRIMARY KEY,
    evaluation_type VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    weight FLOAT DEFAULT 1.0,
    max_score INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === التكاليف ===

CREATE TABLE IF NOT EXISTS labor_monthly_costs (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    month_year VARCHAR(20) NOT NULL,
    basic_salary_cost FLOAT DEFAULT 0,
    resident_allowance_cost FLOAT DEFAULT 0,
    insurance_cost FLOAT DEFAULT 0,
    clothing_allowance_cost FLOAT DEFAULT 0,
    health_card_cost FLOAT DEFAULT 0,
    total_cost FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(employee_id, month_year)
);

CREATE TABLE IF NOT EXISTS contractor_annual_costs (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    tax_amount FLOAT DEFAULT 500000,
    zakat_amount FLOAT DEFAULT 75000,
    is_paid BOOLEAN DEFAULT FALSE,
    paid_date DATE,
    payment_reference VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(year, company_id)
);

-- === العقود ===

CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    contract_type VARCHAR(20),
    contract_value FLOAT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    amount_received FLOAT DEFAULT 0,
    remaining_amount FLOAT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
    invoice_number VARCHAR(50) UNIQUE,
    amount FLOAT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE,
    is_paid BOOLEAN DEFAULT FALSE,
    paid_date DATE,
    paid_amount FLOAT DEFAULT 0,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    journal_entry_id INTEGER REFERENCES journal_entries(id) ON DELETE SET NULL
);

-- === إعدادات الوجبات ===

CREATE TABLE IF NOT EXISTS meal_deductions (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    deduction_type VARCHAR(50) NOT NULL,
    amount FLOAT NOT NULL DEFAULT 0,
    deduction_date DATE NOT NULL,
    description VARCHAR(200),
    is_transferred BOOLEAN DEFAULT FALSE,
    transferred_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    expense_account_code VARCHAR(20),
    receivable_account_code VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS meal_deduction_settings (
    id SERIAL PRIMARY KEY,
    deduction_type VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    default_amount FLOAT DEFAULT 0,
    account_code VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === خطط العمل ===

CREATE TABLE IF NOT EXISTS work_plans (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    plan_type VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    plan_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE,
    assigned_to INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_plan_tasks (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES work_plans(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    "order" INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    completed_by INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    assigned_to INTEGER REFERENCES employees(id) ON DELETE SET NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    estimated_hours FLOAT,
    evaluation_score INTEGER,
    evaluation_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- === تحضير الحضور ===

CREATE TABLE IF NOT EXISTS attendance_preparations (
    id SERIAL PRIMARY KEY,
    month_year VARCHAR(20) NOT NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    region VARCHAR(100),
    preparation_date DATE DEFAULT CURRENT_DATE,
    is_processed BOOLEAN DEFAULT FALSE,
    processed_date DATE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attendance_preparation_details (
    id SERIAL PRIMARY KEY,
    preparation_id INTEGER NOT NULL REFERENCES attendance_preparations(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    attendance_days INTEGER DEFAULT 0,
    absent_days INTEGER DEFAULT 0,
    sick_days INTEGER DEFAULT 0,
    late_minutes_total INTEGER DEFAULT 0,
    overtime_hours FLOAT DEFAULT 0,
    daily_allowance FLOAT DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(preparation_id, employee_id)
);

-- === تحويل الفترات ===

CREATE TABLE IF NOT EXISTS attendance_period_transfers (
    id SERIAL PRIMARY KEY,
    period_name VARCHAR(100) NOT NULL,
    payroll_type VARCHAR(20) NOT NULL DEFAULT 'admin',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    transfer_date DATE DEFAULT CURRENT_DATE,
    is_transferred BOOLEAN DEFAULT FALSE,
    transferred_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    region VARCHAR(100),
    total_employees INTEGER DEFAULT 0,
    total_attendance_days INTEGER DEFAULT 0,
    total_salaries FLOAT DEFAULT 0,
    total_deductions FLOAT DEFAULT 0,
    total_net FLOAT DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(payroll_type, company_id, region, start_date, end_date)
);

CREATE TABLE IF NOT EXISTS attendance_period_transfer_details (
    id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL REFERENCES attendance_period_transfers(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    salary_id INTEGER REFERENCES salaries(id) ON DELETE SET NULL,
    attendance_days INTEGER DEFAULT 0,
    absent_days INTEGER DEFAULT 0,
    sick_days INTEGER DEFAULT 0,
    late_minutes_total INTEGER DEFAULT 0,
    overtime_hours FLOAT DEFAULT 0,
    daily_allowance FLOAT DEFAULT 0,
    base_salary FLOAT DEFAULT 0,
    attendance_amount FLOAT DEFAULT 0,
    overtime_amount FLOAT DEFAULT 0,
    daily_allowance_amount FLOAT DEFAULT 0,
    advance_amount FLOAT DEFAULT 0,
    deduction_amount FLOAT DEFAULT 0,
    penalty_amount FLOAT DEFAULT 0,
    absence_deduction FLOAT DEFAULT 0,
    total_additions FLOAT DEFAULT 0,
    total_deductions FLOAT DEFAULT 0,
    final_amount FLOAT DEFAULT 0,
    is_processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(transfer_id, employee_id)
);


-- =====================================================
-- الجزء 3: إدخال البيانات الأساسية (Seed Data)
-- =====================================================

-- === الحسابات المحاسبية ===

-- الحسابات الرئيسية
INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '1', 'Assets', 'الأصول', 'asset', 'debit', NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '1');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '2', 'Liabilities', 'الخصوم', 'liability', 'credit', NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '2');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '3', 'Equity', 'حقوق الملكية', 'equity', 'credit', NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '3');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '4', 'Revenue', 'الإيرادات', 'revenue', 'credit', NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '4');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '5', 'Expenses', 'المصروفات', 'expense', 'debit', NULL, 1
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '5');

-- الأصول المتداولة
INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '11', 'Current Assets', 'الأصول المتداولة', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '1'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '11');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '110001', 'Cash', 'الصندوق', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '11'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '110001');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '110002', 'Bank', 'البنك', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '11'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '110002');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '12', 'Receivables', 'المدينة', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '1'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '12');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '120001', 'Company Receivables', 'المدينة على الشركات', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '12'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '120001');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '13', 'Advances', 'سلف', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '1'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '13');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '130001', 'Employee Advances', 'سلف الموظفين', 'asset', 'debit', (SELECT id FROM accounts WHERE code = '13'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '130001');

-- الخصوم
INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '21', 'Current Liabilities', 'الخصوم المتداولة', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '2'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '21');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '210001', 'Salary Payable', 'رواتب مستحقة الدفع', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '21'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '210001');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '211003', 'Insurance Payable', 'تأمينات مستحقة', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '21'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '211003');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '211004', 'Health Card Payable', 'بطاقات صحية مستحقة', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '21'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '211004');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '211005', 'Clothing Allowance Payable', 'بدل ملابس مستحق', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '21'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '211005');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '22', 'Payables', 'الدائن', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '2'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '22');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '220001', 'Supplier Payables', 'المدفوعات للموردين', 'liability', 'credit', (SELECT id FROM accounts WHERE code = '22'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '220001');

-- الإيرادات
INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '41', 'Service Revenue', 'إيرادات خدمات', 'revenue', 'credit', (SELECT id FROM accounts WHERE code = '4'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '41');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '410004', 'Agricultural Services Revenue', 'إيرادات خدمات زراعية', 'revenue', 'credit', (SELECT id FROM accounts WHERE code = '41'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '410004');

-- المصروفات
INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '51', 'Operating Expenses', 'مصروفات تشغيلية', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '5'), 2
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '51');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510001', 'Salary Expense', 'مصروف رواتب', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510001');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510002', 'Deduction Expense', 'مصروفخصومات', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510002');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510003', 'Insurance Expense', 'مصروف تأمينات', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510003');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510004', 'Health Card Expense', 'مصروف بطاقات صحية', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510004');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510005', 'Clothing Allowance Expense', 'مصروف بدل ملابس', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510005');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '510006', 'Overtime Expense', 'مصروف إضافي', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '510006');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '520001', 'Cafeteria Expense', 'مصروف كافتيريا', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '520001');

INSERT INTO accounts (code, name, name_ar, account_type, nature, parent_id, level)
SELECT '520002', 'Restaurant Expense', 'مصروف مطعم', 'expense', 'debit', (SELECT id FROM accounts WHERE code = '51'), 3
WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '520002');


-- === أنواع الإجازات ===

INSERT INTO leave_types (name, name_ar, days_per_year, is_paid)
SELECT 'Annual', 'سنوية', 30, TRUE
WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE name = 'Annual');

INSERT INTO leave_types (name, name_ar, days_per_year, is_paid)
SELECT 'Sick', 'مرضية', 999, TRUE
WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE name = 'Sick');

INSERT INTO leave_types (name, name_ar, days_per_year, is_paid)
SELECT 'Maternity', 'أمومة', 60, TRUE
WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE name = 'Maternity');

INSERT INTO leave_types (name, name_ar, days_per_year, is_paid)
SELECT 'Unpaid', 'بدون أجر', 0, FALSE
WHERE NOT EXISTS (SELECT 1 FROM leave_types WHERE name = 'Unpaid');


-- === الإعدادات النظامية ===

INSERT INTO system_settings (setting_key, setting_name, setting_name_ar, value, value_type, category, display_order)
SELECT 'monthly_insurance', 'Monthly Insurance', 'التأمين الشهري', 10800, 'monthly', 'deduction', 1
WHERE NOT EXISTS (SELECT 1 FROM system_settings WHERE setting_key = 'monthly_insurance');

INSERT INTO system_settings (setting_key, setting_name, setting_name_ar, value, value_type, category, display_order)
SELECT 'monthly_health', 'Monthly Health Card', 'البطاقة الصحية الشهرية', 1250, 'monthly', 'deduction', 2
WHERE NOT EXISTS (SELECT 1 FROM system_settings WHERE setting_key = 'monthly_health');

INSERT INTO system_settings (setting_key, setting_name, setting_name_ar, value, value_type, category, display_order)
SELECT 'monthly_clothing', 'Monthly Clothing Allowance', 'بدل الملابس الشهري', 2040, 'monthly', 'allowance', 3
WHERE NOT EXISTS (SELECT 1 FROM system_settings WHERE setting_key = 'monthly_clothing');


-- === المستخدم الافتراضي ===

-- إنشاء مستخدم admin إذا لم يكن موجوداً
INSERT INTO users (username, password, full_name, role, is_active)
SELECT 'admin', 'pbkdf2:sha256:600000$dev-salt$hash-of-admin123', 'مدير النظام', 'admin', TRUE
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');


-- =====================================================
-- الجزء 4: تحديث البيانات القديمة
-- =====================================================

-- تحديث basic_salary للموظفين الذين لم يكونوا להם هذه القيمة
UPDATE employees SET basic_salary = salary WHERE basic_salary = 2000 AND salary > 0;

-- تحديث total_salary إذا لم يكن موجوداً
UPDATE employees SET total_salary = salary WHERE total_salary = 60000 AND salary > 0;


-- =====================================================
-- ملاحظات مهمة:
-- =====================================================
-- 1. هذا السكريبت آمن للتشغيل المتكرر (IF NOT EXISTS)
-- 2. جميع البيانات القديمة محافوظة
-- 3. يتم إضافة الأعمدة الجديدة فقط إذا لم تكن موجودة
-- 4. يتم إنشاء الجداول الجديدة فقط إذا لم تكن موجودة
-- 5. يتم إدخال البيانات الأساسية فقط إذا لم تكن موجودة
-- 6. يجب تشغيل هذا السكريبت مرة واحدة فقط
-- 7. يُنصح بعمل نسخة احتياطية قبل التشغيل
-- =====================================================
