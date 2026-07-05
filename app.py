from flask import Flask, jsonify, request, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress
from flask_talisman import Talisman
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import logging
import sqlalchemy as sa

from config import Config
from models import db, User, WorkPlan, WorkPlanTask, Company, Region, Location, Employee, Supplier, LeaveType, FinancialPeriod, Account, SystemSettings
from blueprints import register_all_blueprints

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect()
csrf.init_app(app)

Compress(app)

database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db.init_app(app)

Talisman(
    app,
    content_security_policy=None,
    force_https=False,
    session_cookie_secure=False
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

@login_manager.unauthorized_handler
def unauthorized():
    if request_wants_json():
        return jsonify(error='Unauthorized', message='يرجى تسجيل الدخول'), 401
    return redirect(url_for('auth.login'))

@app.before_request
def log_request():
    if request.path.startswith('/api/'):
        from flask_login import current_user
        uid = getattr(current_user, 'id', 'anon') if current_user.is_authenticated else 'anon'
        logging.info(f"API {request.method} {request.path} user={uid}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def utility_processor():
    return {
        'now': datetime.now(),
        'app_name': 'طلعت هائل للخدمات والاستشارات الزراعية'
    }

@app.template_filter('currency')
def currency_filter(value):
    try:
        if value is None:
            return "0"
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return "0"

register_all_blueprints(app)

_alias_rules = [
    ('index', '/', 'auth.index'),
    ('login', '/login', 'auth.login'),
    ('logout', '/logout', 'auth.logout'),
    ('users_list', '/users', 'auth.users_list'),
    ('add_user', '/users/add', 'auth.add_user'),
    ('delete_user', '/users/delete/<int:user_id>', 'auth.delete_user'),
    ('check_username', '/check-username', 'auth.check_username'),
    ('employees_list', '/employees', 'employees.employees_list'),
    ('import_employees', '/employees/import', 'employees.import_employees'),
    ('add_employee', '/employees/add', 'employees.add_employee'),
    ('edit_employee', '/employees/edit/<int:emp_id>', 'employees.edit_employee'),
    ('delete_employee', '/employees/delete/<int:emp_id>', 'employees.delete_employee'),
    ('employees_api', '/employees/api/list', 'employees.employees_api'),
    ('employees_by_company_api', '/employees/api/company/<int:company_id>', 'employees.employees_by_company_api'),
    ('check_card_number', '/employees/check_card', 'employees.check_card_number'),
    ('check_employee_code', '/employees/check_code', 'employees.check_employee_code'),
    ('attendance_list', '/attendance', 'attendance.attendance_list'),
    ('add_attendance', '/attendance/add', 'attendance.add_attendance'),
    ('remove_attendance', '/attendance/remove', 'attendance.remove_attendance'),
    ('group_attendance', '/attendance/group', 'attendance.group_attendance'),
    ('save_bulk_attendance', '/attendance/bulk_save', 'attendance.save_bulk_attendance'),
    ('edit_attendance', '/attendance/edit/<int:attendance_id>', 'attendance.edit_attendance'),
    ('delete_attendance_record', '/attendance/delete/<int:attendance_id>', 'attendance.delete_attendance_record'),
    ('period_transfer_list', '/attendance/period-transfer', 'attendance.period_transfer_list'),
    ('create_management_transfer', '/attendance/period-transfer/create-management', 'attendance.create_management_transfer'),
    ('transfer_period_to_salary', '/attendance/period-transfer/transfer-to-salary/<int:transfer_id>', 'attendance.transfer_period_to_salary'),
    ('refresh_period_transfer', '/attendance/period-transfer/refresh/<int:transfer_id>', 'attendance.refresh_period_transfer'),
    ('view_period_transfer', '/attendance/period-transfer/view/<int:transfer_id>', 'attendance.view_period_transfer'),
    ('create_period_transfer', '/attendance/period-transfer/create', 'attendance.create_period_transfer'),
    ('delete_period_transfer', '/attendance/period-transfer/delete/<int:transfer_id>', 'attendance.delete_period_transfer'),
    ('edit_period_transfer', '/attendance/period-transfer/edit/<int:transfer_id>', 'attendance.edit_period_transfer'),
    ('force_delete_period_transfer', '/attendance/period-transfer/force-delete/<int:transfer_id>', 'attendance.force_delete_period_transfer'),
    ('companies_dashboard', '/companies', 'companies.companies_dashboard'),
    ('companies_list', '/companies', 'companies.companies_dashboard'),
    ('company_details', '/companies/<int:company_id>', 'companies.company_details'),
    ('add_company', '/companies/add', 'companies.add_company'),
    ('edit_company', '/companies/<int:company_id>/edit', 'companies.edit_company'),
    ('delete_company', '/companies/<int:company_id>/delete', 'companies.delete_company'),
    ('add_region', '/companies/regions/add', 'companies.add_region'),
    ('edit_region', '/companies/regions/<int:region_id>/edit', 'companies.edit_region'),
    ('delete_region', '/companies/regions/<int:region_id>/delete', 'companies.delete_region'),
    ('add_location', '/companies/locations/add', 'companies.add_location'),
    ('edit_location', '/companies/locations/<int:location_id>/edit', 'companies.edit_location'),
    ('delete_location', '/companies/locations/<int:location_id>/delete', 'companies.delete_location'),
    ('evaluations_list', '/evaluations', 'evaluations.evaluations_list'),
    ('add_evaluation', '/evaluations/add', 'evaluations.add_evaluation'),
    ('add_supervisor_evaluation', '/evaluations/add_supervisor', 'evaluations.add_supervisor_evaluation'),
    ('area_evaluations_list', '/evaluations/areas', 'evaluations.area_evaluations_list'),
    ('add_area_evaluation', '/evaluations/areas/add', 'evaluations.add_area_evaluation'),
    ('view_area_evaluation', '/evaluations/areas/view/<int:evaluation_id>', 'evaluations.view_area_evaluation'),
    ('edit_area_evaluation', '/evaluations/areas/edit/<int:evaluation_id>', 'evaluations.edit_area_evaluation'),
    ('delete_area_evaluation', '/evaluations/areas/delete/<int:evaluation_id>', 'evaluations.delete_area_evaluation'),
    ('manage_area_criteria', '/evaluations/areas/criteria', 'evaluations.manage_area_criteria'),
    ('delete_area_criteria', '/evaluations/areas/criteria/delete/<int:criteria_id>', 'evaluations.delete_area_criteria'),
    ('evaluation_criteria_list', '/evaluation-criteria', 'evaluations.evaluation_criteria_list'),
    ('add_evaluation_criteria_form', '/evaluation-criteria/add', 'evaluations.add_evaluation_criteria_form'),
    ('add_evaluation_criteria', '/evaluation-criteria/add', 'evaluations.add_evaluation_criteria'),
    ('edit_evaluation_criteria_form', '/evaluation-criteria/edit/<int:id>', 'evaluations.edit_evaluation_criteria_form'),
    ('edit_evaluation_criteria', '/evaluation-criteria/edit/<int:id>', 'evaluations.edit_evaluation_criteria'),
    ('delete_evaluation_criteria', '/evaluation-criteria/delete/<int:id>', 'evaluations.delete_evaluation_criteria'),
    ('financial_dashboard', '/financial/dashboard', 'financial.financial_dashboard'),
    ('salaries_list', '/financial/salaries', 'financial.salaries_list'),
    ('salary_calculation', '/financial/salary_calculation', 'financial.salary_calculation'),
    ('pay_salary', '/financial/salaries/pay/<int:salary_id>', 'financial.pay_salary'),
    ('bulk_pay_salaries', '/financial/salaries/bulk_pay', 'financial.bulk_pay_salaries'),
    ('export_salaries_excel', '/financial/salaries/export', 'financial.export_salaries_excel'),
    ('transactions_list', '/financial/transactions', 'financial.transactions_list'),
    ('add_transaction', '/financial/add_transaction', 'financial.add_transaction'),
    ('delete_transaction', '/financial/delete_transaction/<int:trans_id>', 'financial.delete_transaction'),
    ('bulk_transfer_transactions', '/financial/bulk_transfer', 'financial.bulk_transfer_transactions'),
    ('edit_transaction', '/financial/transaction/<int:trans_id>/edit', 'financial.edit_transaction'),
    ('transactions_report', '/financial/transactions/report', 'financial.transactions_report'),
    ('reverse_transaction', '/financial/reverse_transaction/<int:trans_id>', 'financial.reverse_transaction'),
    ('transfer_transaction_to_salary', '/financial/transfer_to_salary', 'financial.transfer_transaction_to_salary'),
    ('transfer_transaction_to_preparation', '/financial/transfer_to_preparation', 'financial.transfer_transaction_to_preparation'),
    ('settle_cash', '/financial/cash/settle', 'financial.settle_cash'),
    ('collect_customers', '/financial/collect-customers', 'financial.collect_customers'),
    ('meal_deductions_list', '/meal-deductions', 'financial.meal_deductions_list'),
    ('meal_deduction_settings', '/meal-deductions', 'financial.meal_deductions_list'),
    ('add_meal_deduction', '/meal-deductions/add', 'financial.add_meal_deduction'),
    ('contracts_list', '/contracts', 'financial.contracts_list'),
    ('add_contract', '/contracts/add', 'financial.add_contract'),
    ('generate_monthly_invoices', '/contracts/generate-monthly-invoices', 'financial.generate_monthly_invoices'),
    ('invoices_list', '/invoices', 'financial.invoices_list'),
    ('add_invoice', '/invoices/add', 'financial.add_invoice'),
    ('edit_invoice', '/invoices/edit/<int:invoice_id>', 'financial.edit_invoice'),
    ('delete_invoice', '/invoices/delete/<int:invoice_id>', 'financial.delete_invoice'),
    ('pay_invoice', '/invoices/pay/<int:invoice_id>', 'financial.pay_invoice'),
    ('print_invoice', '/invoices/print/<int:invoice_id>', 'financial.print_invoice'),
    ('invoice_partial_payments', '/invoices/partial_payments/<int:invoice_id>', 'financial.invoice_partial_payments'),
    ('accounts_dashboard', '/accounts', 'accounts.accounts_dashboard'),
    ('chart_of_accounts', '/accounts/chart', 'accounts.chart_of_accounts'),
    ('add_account', '/accounts/add', 'accounts.add_account'),
    ('edit_account', '/accounts/edit/<int:account_id>', 'accounts.edit_account'),
    ('delete_account', '/accounts/delete/<int:account_id>', 'accounts.delete_account'),
    ('activate_account', '/accounts/activate/<int:account_id>', 'accounts.activate_account'),
    ('journal_entries_list', '/accounts/journal', 'accounts.journal_entries_list'),
    ('add_journal_entry', '/accounts/journal/add', 'accounts.add_journal_entry'),
    ('reverse_journal_entry_view', '/accounts/reverse_entry/<int:entry_id>', 'accounts.reverse_journal_entry_view'),
    ('transfer_between_accounts', '/accounts/transfer', 'accounts.transfer_between_accounts'),
    ('zero_out_account', '/accounts/zero-out', 'accounts.zero_out_account'),
    ('transfer_history', '/accounts/transfer-history', 'accounts.transfer_history'),
    ('trial_balance', '/accounts/trial_balance', 'accounts.trial_balance'),
    ('income_statement', '/accounts/income_statement', 'accounts.income_statement'),
    ('balance_sheet', '/accounts/balance_sheet', 'accounts.balance_sheet'),
    ('cash_flow_statement', '/accounts/cash_flow', 'accounts.cash_flow_statement'),
    ('close_expenses_api', '/accounts/close-expenses', 'accounts.close_expenses_api'),
    ('reopen_period_api', '/accounts/reopen-period', 'accounts.reopen_period_api'),
    ('redistribute_expenses_api', '/accounts/redistribute-expenses', 'accounts.redistribute_expenses_api'),
    ('get_expense_details', '/accounts/expense-details', 'accounts.get_expense_details'),
    ('check_closing_status', '/accounts/check-closing-status', 'accounts.check_closing_status'),
    ('suppliers_list', '/suppliers', 'suppliers.suppliers_list'),
    ('add_supplier', '/suppliers/add', 'suppliers.add_supplier'),
    ('edit_supplier', '/suppliers/edit/<int:supplier_id>', 'suppliers.edit_supplier'),
    ('delete_supplier', '/suppliers/delete/<int:supplier_id>', 'suppliers.delete_supplier'),
    ('supplier_invoices_list', '/supplier-invoices', 'suppliers.supplier_invoices_list'),
    ('add_supplier_invoice', '/supplier-invoices/add', 'suppliers.add_supplier_invoice'),
    ('edit_supplier_invoice', '/supplier-invoices/edit/<int:invoice_id>', 'suppliers.edit_supplier_invoice'),
    ('delete_supplier_invoice', '/supplier-invoices/delete/<int:invoice_id>', 'suppliers.delete_supplier_invoice'),
    ('pay_supplier_invoice', '/supplier-invoices/pay/<int:invoice_id>', 'suppliers.pay_supplier_invoice'),
    ('supplier_invoices_report', '/supplier-invoices/report', 'suppliers.supplier_invoices_report'),
    ('print_supplier_invoice', '/supplier-invoices/print/<int:invoice_id>', 'suppliers.print_supplier_invoice'),
    ('expense_categories_list', '/expense-categories', 'suppliers.expense_categories_list'),
    ('add_expense_category', '/expense-categories/add', 'suppliers.add_expense_category'),
    ('edit_expense_category', '/expense-categories/edit/<int:category_id>', 'suppliers.edit_expense_category'),
    ('delete_expense_category', '/expense-categories/delete/<int:category_id>', 'suppliers.delete_expense_category'),
    ('toggle_expense_category', '/expense-categories/toggle/<int:category_id>', 'suppliers.toggle_expense_category'),
    ('add_expense_invoice', '/supplier-invoices/add', 'suppliers.add_supplier_invoice'),
    ('expense_invoices_list', '/supplier-invoices', 'suppliers.supplier_invoices_list'),
    ('reports_dashboard', '/reports/dashboard', 'reports_bp.reports_dashboard'),
    ('attendance_report', '/reports/attendance', 'reports_bp.attendance_report'),
    ('financial_report', '/reports/financial', 'reports_bp.financial_report'),
    ('employees_report', '/reports/employees', 'reports_bp.employees_report'),
    ('regions_report', '/reports/regions', 'reports_bp.regions_report'),
    ('monthly_close', '/reports/monthly_close', 'reports_bp.monthly_close'),
    ('financial_monthly_report', '/reports/financial_monthly', 'reports_bp.financial_monthly_report'),
    ('evaluations_analysis_report', '/reports/evaluations_analysis', 'reports_bp.evaluations_analysis_report'),
    ('evaluations_by_location_report', '/reports/evaluations_by_location', 'reports_bp.evaluations_by_location_report'),
    ('evaluations_by_region_report', '/reports/evaluations_by_region', 'reports_bp.evaluations_by_region_report'),
    ('export_evaluations_by_region_pdf', '/reports/evaluations_by_region/pdf', 'reports_bp.export_evaluations_by_region_pdf'),
    ('export_evaluations_by_location_pdf', '/reports/evaluations_by_location/pdf', 'reports_bp.export_evaluations_by_location_pdf'),
    ('export_attendance_pdf', '/reports/attendance/pdf', 'reports_bp.export_attendance_pdf'),
    ('export_financial_pdf', '/reports/financial/pdf', 'reports_bp.export_financial_pdf'),
    ('export_attendance_excel', '/reports/attendance/export', 'reports_bp.export_attendance_excel'),
    ('export_salaries_excel_reports', '/reports/salaries/export', 'reports_bp.export_salaries_excel'),
    ('labor_costs_report', '/labor/costs/report', 'labor_bp.labor_costs_report'),
    ('calculate_labor_costs', '/labor/costs/calculate', 'labor_bp.calculate_labor_costs'),
    ('create_labor_costs_journal', '/labor/costs/journal/<int:transfer_id>', 'labor_bp.create_labor_costs_journal'),
    ('view_labor_costs', '/labor/costs/view/<int:transfer_id>', 'labor_bp.view_labor_costs'),
    ('contractor_annual_costs', '/labor/contractor/annual', 'labor_bp.contractor_annual_costs'),
    ('create_contractor_journal', '/labor/contractor/journal/<int:year>', 'labor_bp.create_contractor_journal'),
    ('system_settings_all', '/system/settings', 'settings_bp.system_settings_all'),
    ('system_settings', '/system/settings', 'settings_bp.system_settings_all'),
    ('update_system_settings', '/system/settings/update', 'settings_bp.update_system_settings'),
    ('add_allowance', '/system/settings/add-allowance', 'settings_bp.add_allowance'),
    ('edit_allowance', '/system/settings/edit-allowance/<int:allowance_id>', 'settings_bp.edit_allowance'),
    ('delete_allowance', '/system/settings/delete-allowance/<int:allowance_id>', 'settings_bp.delete_allowance'),
    ('attendance_preparation_list', '/attendance', 'attendance.attendance_list'),
    ('create_attendance_preparation', '/attendance/add', 'attendance.add_attendance'),
    ('edit_attendance_preparation', '/attendance/edit/<int:attendance_id>', 'attendance.edit_attendance'),
    ('reverse_invoice', '/invoices/reverse/<int:invoice_id>', 'financial.reverse_invoice'),
    ('auto_generate_contract_invoices', '/contracts/auto-generate/<int:contract_id>', 'financial.auto_generate_contract_invoices'),
    ('generate_all_future_invoices', '/contracts/generate-all-future-invoices/<int:contract_id>', 'financial.generate_all_future_invoices'),
    ('meal_deduction_settings', '/meal-deductions', 'financial.meal_deductions_list'),
    ('edit_attendance', '/attendance/edit/<int:attendance_id>', 'attendance.edit_attendance_record'),
]

_seen_rules = set()
for old_name, rule, new_endpoint in _alias_rules:
    if old_name not in app.view_functions:
        view_func = app.view_functions.get(new_endpoint)
        if view_func and rule not in _seen_rules:
            try:
                app.add_url_rule(rule, old_name, view_func)
                _seen_rules.add(rule)
            except AssertionError:
                pass

@app.errorhandler(404)
def not_found(e):
    if request_wants_json():
        return jsonify(error='Not found'), 404
    if _has_react_dist:
        from flask import send_from_directory
        return send_from_directory(_react_dist, 'index.html'), 200
    from flask import render_template
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    if request_wants_json():
        return jsonify(error='Internal server error'), 500
    from flask import render_template
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    if request_wants_json():
        return jsonify(error='Forbidden'), 403
    from flask import render_template
    return render_template('errors/403.html'), 403

def request_wants_json():
    return request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json'

@app.route('/debug/dist-info')
def debug_dist_info():
    base = _os.path.dirname(_os.path.abspath(__file__))
    cwd = _os.getcwd()
    result = {
        'base': base,
        'cwd': cwd,
        'react_dist': _react_dist if '_react_dist' in dir() else 'not set',
        'has_react_dist': _has_react_dist if '_has_react_dist' in dir() else False,
    }
    try:
        from models import db as _db
        from sqlalchemy import text as _text
        _db.session.execute(_text('SELECT 1'))
        result['db_ok'] = True
        try:
            rows = _db.session.execute(_text('SELECT COUNT(*) FROM attendances')).scalar()
            result['attendance_count'] = rows
        except Exception as e:
            result['attendance_error'] = str(e)
        try:
            rows = _db.session.execute(_text('SELECT COUNT(*) FROM employees')).scalar()
            result['employee_count'] = rows
        except Exception as e:
            result['employee_error'] = str(e)
        try:
            cols = _db.session.execute(_text("SELECT column_name FROM information_schema.columns WHERE table_name='attendances'")).fetchall()
            result['attendance_columns'] = [c[0] for c in cols]
        except Exception as e:
            result['schema_error'] = str(e)
    except Exception as e:
        result['db_ok'] = False
        result['db_error'] = str(e)
    return jsonify(result)


# ==================== Serve React Build (Production) ====================
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))
_react_dist = _os.path.join(_base, 'frontend', 'dist')
if not _os.path.isdir(_react_dist):
    _react_dist = _os.path.join(_base, 'dist')
if not _os.path.isdir(_react_dist):
    _react_dist = _os.path.join(_os.getcwd(), 'frontend', 'dist')
if not _os.path.isdir(_react_dist):
    _react_dist = _os.path.join(_os.getcwd(), 'dist')
if _os.path.isdir(_react_dist):
    from flask import send_from_directory as _send_from_directory
    _has_react_dist = True
    print(f"React dist found at: {_react_dist}")

    @app.route('/')
    def serve_react_root():
        return _send_from_directory(_react_dist, 'index.html')

    @app.route('/<path:path>')
    def serve_react_static(path):
        if path.startswith('api/') or path.startswith('auth/') or path.startswith('static/'):
            from flask import abort
            abort(404)
        file_path = _os.path.join(_react_dist, path)
        if _os.path.isfile(file_path):
            return _send_from_directory(_react_dist, path)
        return _send_from_directory(_react_dist, 'index.html')
else:
    _has_react_dist = False
    print(f"React dist NOT found! Checked:")
    print(f"  1. {_os.path.join(_base, 'frontend', 'dist')} -> {_os.path.isdir(_os.path.join(_base, 'frontend', 'dist'))}")
    print(f"  2. {_os.path.join(_base, 'dist')} -> {_os.path.isdir(_os.path.join(_base, 'dist'))}")
    print(f"  3. {_os.path.join(_os.getcwd(), 'frontend', 'dist')} -> {_os.path.isdir(_os.path.join(_os.getcwd(), 'frontend', 'dist'))}")
    print(f"  4. {_os.path.join(_os.getcwd(), 'dist')} -> {_os.path.isdir(_os.path.join(_os.getcwd(), 'dist'))}")
    print(f"  CWD: {_os.getcwd()}")
    print(f"  __file__: {__file__}")
    try:
        print(f"  Contents of base: {_os.listdir(_base)}")
    except:
        pass

    @app.route('/')
    def serve_fallback():
        return render_template('landing.html')


def auto_migrate():
    """إضافة أعمدة جديدة للجداول الموجودة تلقائياً - آمن للتشغيل المتكرر"""
    inspector = sa.inspect(db.engine)

    def add_column(table, column, col_type, default=None):
        try:
            cols = [c['name'] for c in inspector.get_columns(table)]
        except Exception:
            return
        if column not in cols:
            if default is not None:
                sql = f'ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}'
            else:
                sql = f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'
            try:
                db.session.execute(sa.text(sql))
                db.session.commit()
                print(f"  + {table}.{column}")
            except Exception as e:
                db.session.rollback()
                if 'already exists' not in str(e).lower():
                    print(f"  ! {table}.{column}: {e}")

    print("Auto-migration: checking columns...")
    add_column('users', 'employee_id', 'INTEGER')
    add_column('users', 'allowed_pages', 'TEXT')

    add_column('employees', 'supervisor_id', 'INTEGER')
    add_column('employees', 'basic_salary', 'FLOAT', '2000')
    add_column('employees', 'clothing_allowance', 'FLOAT', '24480')
    add_column('employees', 'health_card_allowance', 'FLOAT', '15000')
    add_column('employees', 'monthly_insurance', 'FLOAT', '10800')
    add_column('employees', 'contractor_tax', 'FLOAT', '500000')
    add_column('employees', 'contractor_zakat', 'FLOAT', '75000')
    add_column('employees', 'daily_allowance', 'FLOAT', '500')
    add_column('employees', 'total_salary', 'FLOAT', '60000')
    add_column('employees', 'allowances_updated_at', 'TIMESTAMP')
    add_column('employees', 'region_id', 'INTEGER')
    add_column('employees', 'user_id', 'INTEGER')
    add_column('employees', 'worker_type', "VARCHAR(20)", "'permanent'")

    add_column('financial_transactions', 'payment_method', "VARCHAR(20)", "'cash'")
    add_column('financial_transactions', 'supplier_id', 'INTEGER')
    add_column('financial_transactions', 'monthly_installment', 'FLOAT', '0')
    add_column('financial_transactions', 'settled_amount', 'FLOAT', '0')
    add_column('financial_transactions', 'journal_entry_id', 'INTEGER')

    add_column('salaries', 'cafeteria_supplier_id', 'INTEGER')
    add_column('salaries', 'restaurant_supplier_id', 'INTEGER')
    add_column('salaries', 'cafeteria_paid_to_supplier', 'BOOLEAN', 'FALSE')
    add_column('salaries', 'restaurant_paid_to_supplier', 'BOOLEAN', 'FALSE')
    add_column('salaries', 'contractor_profit', 'NUMERIC(12,2)', '0')
    add_column('salaries', 'is_calculated', 'BOOLEAN', 'FALSE')
    add_column('salaries', 'calculated_at', 'TIMESTAMP')

    add_column('companies', 'receivable_account_id', 'INTEGER')

    add_column('suppliers', 'payable_account_id', 'INTEGER')
    add_column('suppliers', 'name_ar', "VARCHAR(200)", "''")
    add_column('suppliers', 'supplier_type', "VARCHAR(50)", "'general'")

    add_column('evaluation_criteria', 'company_id', 'INTEGER')

    add_column('evaluations', 'region_id', 'INTEGER')
    add_column('evaluations', 'location_id', 'INTEGER')

    add_column('invoices', 'journal_entry_id', 'INTEGER')

    add_column('attendances', 'sick_leave', 'BOOLEAN', 'FALSE')
    add_column('attendances', 'sick_leave_days', 'INTEGER', '0')
    add_column('attendances', 'annual_leave_days', 'INTEGER', '0')

    print("Auto-migration: column check complete")


def init_db():
    try:
        with app.app_context():
            auto_migrate()
            db.create_all()
            print("Database tables created/verified")
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    password=generate_password_hash('admin123'),
                    full_name='مدير النظام',
                    role='admin'
                )
                db.session.add(admin)
                print("Created admin user")
                db.session.commit()
            else:
                print("Admin user exists")

            # تهيئة أنواع الإجازات
            if LeaveType.query.count() == 0:
                leave_types = [
                    LeaveType(name='Annual Leave', name_ar='إجازة سنوية', days_per_year=30, is_paid=True),
                    LeaveType(name='Sick Leave', name_ar='إجازة مرضية', days_per_year=999, is_paid=True),
                    LeaveType(name='Maternity Leave', name_ar='إجازة أمومة', days_per_year=60, is_paid=True),
                    LeaveType(name='Unpaid Leave', name_ar='إجازة بدون راتب', days_per_year=0, is_paid=False),
                ]
                for lt in leave_types:
                    db.session.add(lt)
                db.session.commit()
                print("Created leave types")

            # تهيئة الفترة المالية الحالية
            now = datetime.now()
            current_period = FinancialPeriod.query.filter_by(
                period_type='monthly',
                start_date=datetime(now.year, now.month, 1).date()
            ).first()
            if not current_period:
                if now.month == 12:
                    end_date = datetime(now.year, 12, 31).date()
                else:
                    end_date = datetime(now.year, now.month + 1, 1).date() - timedelta(days=1)
                fp = FinancialPeriod(
                    name=f'فترة {now.month:02d}-{now.year}',
                    period_type='monthly',
                    start_date=datetime(now.year, now.month, 1).date(),
                    end_date=end_date,
                    status='open'
                )
                db.session.add(fp)
                db.session.commit()
                print(f"Created current financial period: {fp.name}")

            seed_accounts()
            seed_system_settings()
            seed_demo_data()
    except Exception as e:
        print(f"Database connection failed: {e}")


def seed_accounts():
    """إدخال الحسابات المحاسبية إذا لم تكن موجودة"""
    if Account.query.count() > 0:
        return

    print("Seeding chart of accounts...")
    accounts_data = [
        ('1', 'Assets', 'الأصول', 'asset', 'debit', None, 1),
        ('11', 'Current Assets', 'الأصول المتداولة', 'asset', 'debit', '1', 2),
        ('110001', 'Cash', 'الصندوق', 'asset', 'debit', '11', 3),
        ('110002', 'Bank', 'البنك', 'asset', 'debit', '11', 3),
        ('12', 'Receivables', 'المدينة', 'asset', 'debit', '1', 2),
        ('120001', 'Company Receivables', 'المدينة على الشركات', 'asset', 'debit', '12', 3),
        ('13', 'Advances', 'سلف', 'asset', 'debit', '1', 2),
        ('130001', 'Employee Advances', 'سلف الموظفين', 'asset', 'debit', '13', 3),
        ('2', 'Liabilities', 'الخصوم', 'liability', 'credit', None, 1),
        ('21', 'Current Liabilities', 'الخصوم المتداولة', 'liability', 'credit', '2', 2),
        ('210001', 'Salary Payable', 'رواتب مستحقة الدفع', 'liability', 'credit', '21', 3),
        ('211003', 'Insurance Payable', 'تأمينات مستحقة', 'liability', 'credit', '21', 3),
        ('211004', 'Health Card Payable', 'بطاقات صحية مستحقة', 'liability', 'credit', '21', 3),
        ('211005', 'Clothing Allowance Payable', 'بدل ملابس مستحق', 'liability', 'credit', '21', 3),
        ('22', 'Payables', 'الدائن', 'liability', 'credit', '2', 2),
        ('220001', 'Supplier Payables', 'المدفوعات للموردين', 'liability', 'credit', '22', 3),
        ('3', 'Equity', 'حقوق الملكية', 'equity', 'credit', None, 1),
        ('4', 'Revenue', 'الإيرادات', 'revenue', 'credit', None, 1),
        ('41', 'Service Revenue', 'إيرادات خدمات', 'revenue', 'credit', '4', 2),
        ('410004', 'Agricultural Services Revenue', 'إيرادات خدمات زراعية', 'revenue', 'credit', '41', 3),
        ('5', 'Expenses', 'المصروفات', 'expense', 'debit', None, 1),
        ('51', 'Operating Expenses', 'مصروفات تشغيلية', 'expense', 'debit', '5', 2),
        ('510001', 'Salary Expense', 'مصروف رواتب', 'expense', 'debit', '51', 3),
        ('510002', 'Deduction Expense', 'مصروفخصومات', 'expense', 'debit', '51', 3),
        ('510003', 'Insurance Expense', 'مصروف تأمينات', 'expense', 'debit', '51', 3),
        ('510004', 'Health Card Expense', 'مصروف بطاقات صحية', 'expense', 'debit', '51', 3),
        ('510005', 'Clothing Allowance Expense', 'مصروف بدل ملابس', 'expense', 'debit', '51', 3),
        ('510006', 'Overtime Expense', 'مصروف إضافي', 'expense', 'debit', '51', 3),
        ('520001', 'Cafeteria Expense', 'مصروف كافتيريا', 'expense', 'debit', '51', 3),
        ('520002', 'Restaurant Expense', 'مصروف مطعم', 'expense', 'debit', '51', 3),
    ]
    code_to_id = {}
    for code, name, name_ar, atype, nature, parent_code, level in accounts_data:
        parent_id = code_to_id.get(parent_code)
        acc = Account(code=code, name=name, name_ar=name_ar, account_type=atype, nature=nature, parent_id=parent_id, level=level)
        db.session.add(acc)
        db.session.flush()
        code_to_id[code] = acc.id
    db.session.commit()
    print(f"Created {len(accounts_data)} accounts")


def seed_system_settings():
    """إدخال إعدادات النظام إذا لم تكن موجودة"""
    if SystemSettings.query.count() > 0:
        return
    print("Seeding system settings...")
    settings = [
        SystemSettings(setting_key='monthly_insurance', setting_name='Monthly Insurance', setting_name_ar='التأمين الشهري', value=10800, value_type='monthly', category='deduction', display_order=1),
        SystemSettings(setting_key='monthly_health', setting_name='Monthly Health Card', setting_name_ar='البطاقة الصحية الشهرية', value=1250, value_type='monthly', category='deduction', display_order=2),
        SystemSettings(setting_key='monthly_clothing', setting_name='Monthly Clothing Allowance', setting_name_ar='بدل الملابس الشهري', value=2040, value_type='monthly', category='allowance', display_order=3),
    ]
    for s in settings:
        db.session.add(s)
    db.session.commit()
    print("Created system settings")


def seed_demo_data():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        return

    if WorkPlan.query.count() > 0:
        return

    from datetime import date, timedelta
    today = date.today()

    companies = Company.query.all()
    regions = Region.query.all()
    locations = Location.query.all()
    employees = Employee.query.all()

    if not companies:
        return

    comp = companies[0]
    reg = regions[0] if regions else None
    loc = locations[0] if locations else None

    demo_plans = [
        {
            'title': 'ري أشجار النخل - المنطقة الشمالية',
            'description': 'ري جميع أشجار النخل في المنطقة الشمالية بالération اليدوية',
            'plan_type': 'daily',
            'company_id': comp.id,
            'region_id': reg.id if reg else None,
            'location_id': loc.id if loc else None,
            'plan_date': today,
            'tasks': [
                ('ري النخل 1-20', 'ري الأشجار من الفجر حتى الساعة 10 صباحاً'),
                ('ري النخل 21-40', 'ري الأشجار من الساعة 10 حتى الظهر'),
                ('فحص صرف المياه', 'التأكد من عدم انسداد مجاري الري'),
                ('تنظيف القنوات', 'تنظيف قنوات الري من الأوساخ'),
            ]
        },
        {
            'title': 'قص وتشكيل أغصان المانجو',
            'description': 'قص الأغصان الزائدة وتشكيل شجر المانجو',
            'plan_type': 'daily',
            'company_id': comp.id,
            'region_id': reg.id if reg else None,
            'location_id': loc.id if loc else None,
            'plan_date': today,
            'tasks': [
                ('قص الأغصان الميتة', 'إزالة جميع الأغصان الميتة والمصابة'),
                ('تشكيل التاج', 'تشكيل تاج الشجرة بشكل منتظم'),
                ('رش المبيد', 'رش الأغصان المقصوصة بمبيد فطري'),
                ('جمع النفايات', 'جمع وتجميع الأغصان المقصوصة'),
                ('كتابة التقرير', 'توثيق أعمال اليوم وتقديم التقرير'),
            ]
        },
        {
            'title': 'خطة شهرية - تسميد المزارع',
            'description': 'خطة تسميد جميع مزارع الشهر الحالي',
            'plan_type': 'monthly',
            'company_id': comp.id,
            'region_id': reg.id if reg else None,
            'plan_date': today,
            'due_date': today + timedelta(days=30),
            'tasks': [
                ('تحليل التربة', 'أخذ عينات من التربة وتحليلها'),
                ('شراء الأسمدة', 'شراء الأسمدة المطلوبة حسب التحليل'),
                ('تطعيم الأشجار', 'تطعيم الأشجار بالأسمدة العضوية'),
                ('الري بعد التسميد', 'ري المزارع بعد 24 ساعة من التسميد'),
                ('متابعة النمو', 'مراقبة نمو الأشجار بعد أسبوع'),
                ('تقرير شهري', 'إعداد تقرير شامل عن حالة المزارع'),
            ]
        },
        {
            'title': 'خطة سنوية - إضمار مزرعة البرتقال',
            'description': 'خطة شاملة لإضمار مزرعة البرتقال لعام 2026',
            'plan_type': 'yearly',
            'company_id': comp.id,
            'plan_date': date(2026, 1, 1),
            'due_date': date(2026, 12, 31),
            'tasks': [
                ('ال季度修剪 (Q1)', 'قص الشتوي الرئيسي'),
                ('ال季度修剪 (Q2)', 'قص الصيفي الخفيف'),
                ('ال季度修剪 (Q3)', 'الإزالة الخضراء'),
                ('ال季度修剪 (Q4)', 'التحضير للشتاء'),
                ('الري الشهري', 'متابعة برنامج الري طوال العام'),
                ('السماد الشهري', 'تطبيق برنامج السماد المتنوع'),
                ('مكافحة الآفات', 'تطبيق برنامج مكافحة الآفات'),
                ('الحصاد', 'حصاد البرتقال في الموعد المناسب'),
                ('التعبئة والتوزيع', 'تعبئة الحصاد وتوزيعه'),
                ('التقرير السنوي', 'إعداد التقرير الختامي'),
            ]
        },
        {
            'title': 'مكافحة الحشرات - اليوم',
            'description': 'رش مبيدات الحشرات في منطقة المزرعة الجنوبية',
            'plan_type': 'daily',
            'company_id': comp.id,
            'region_id': reg.id if reg else None,
            'location_id': loc.id if loc else None,
            'plan_date': today,
            'tasks': [
                ('تحضير المبيد', 'خلط المبيد بالتركيز الصحيح'),
                ('الرش الصباحي', 'رش الأشجار من الساعة 6 إلى 9'),
                ('الرش المسائي', 'رش الأشجار من الساعة 4 إلى 6'),
                ('غسل المعدات', 'تنظيف وغسل معدات الرش'),
            ]
        },
    ]

    for plan_data in demo_plans:
        tasks = plan_data.pop('tasks')
        p = WorkPlan(
            title=plan_data['title'],
            description=plan_data['description'],
            plan_type=plan_data['plan_type'],
            company_id=plan_data.get('company_id'),
            region_id=plan_data.get('region_id'),
            location_id=plan_data.get('location_id'),
            plan_date=plan_data['plan_date'],
            due_date=plan_data.get('due_date'),
            created_by=admin.id,
            status='pending',
        )
        db.session.add(p)
        db.session.flush()

        for i, (title, desc) in enumerate(tasks):
            t = WorkPlanTask(plan_id=p.id, title=title, description=desc, order=i)
            db.session.add(t)

    db.session.commit()
    print(f"Seeded {len(demo_plans)} demo work plans")

    if Supplier.query.filter_by(name='مطعم المزرعة').count() == 0:
        sup_restaurant = Supplier(
            name='مطعم المزرعة', name_ar='مطعم المزرعة',
            supplier_type='restaurant', contact_person='أحمد', phone='0500000001',
        )
        db.session.add(sup_restaurant)
        db.session.flush()

        sup_cafeteria = Supplier(
            name='بوفية العمال', name_ar='بوفية العمال',
            supplier_type='cafeteria', contact_person='محمد', phone='0500000002',
        )
        db.session.add(sup_cafeteria)
        db.session.commit()
        print("Seeded restaurant and cafeteria suppliers")

if not hasattr(app, '_init_db_done'):
    init_db()
    app._init_db_done = True

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
