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
            rows = _db.session.execute(_text('SELECT COUNT(*) FROM employees')).scalar()
            result['employee_count'] = rows
        except Exception as e:
            result['employee_error'] = str(e)
        try:
            cols = _db.session.execute(_text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name='employees' ORDER BY ordinal_position"
            )).fetchall()
            result['employee_columns'] = {c[0]: c[1] for c in cols}
        except Exception as e:
            result['schema_error'] = str(e)
    except Exception as e:
        result['db_ok'] = False
        result['db_error'] = str(e)
    return jsonify(result)

@app.route('/debug/fix-columns')
def debug_fix_columns():
    results = []
    try:
        from models import db as _db
        from sqlalchemy import text as _text
        fixes = [
            ('employees', 'allowances_updated_at', 'TIMESTAMP'),
            ('employees', 'worker_type', 'VARCHAR(20)'),
            ('employees', 'employee_type', 'VARCHAR(20)'),
            ('employees', 'name', 'VARCHAR(100)'),
            ('employees', 'card_number', 'VARCHAR(20)'),
            ('employees', 'code', 'VARCHAR(20)'),
            ('employees', 'job_title', 'VARCHAR(100)'),
            ('employees', 'region', 'VARCHAR(100)'),
            ('employees', 'phone', 'VARCHAR(20)'),
        ]
        for table, column, target in fixes:
            row = _db.session.execute(_text(
                f"SELECT data_type FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND column_name = '{column}'"
            )).fetchone()
            if not row:
                results.append({'col': column, 'status': 'not found'})
                continue
            current = row[0]
            results.append({'col': column, 'current': current, 'target': target})
            if current == target.lower().split('(')[0].strip():
                results.append({'col': column, 'action': 'already correct'})
                continue
            try:
                if 'timestamp' in target.lower():
                    _db.session.execute(_text(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT'))
                    _db.session.execute(_text(f'UPDATE {table} SET {column} = NULL'))
                    _db.session.execute(_text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE {target}'))
                else:
                    _db.session.execute(_text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target} USING {column}::text"))
                _db.session.commit()
                results.append({'col': column, 'action': f'fixed to {target}'})
            except Exception as e:
                _db.session.rollback()
                results.append({'col': column, 'error': str(e)[:200]})
    except Exception as e:
        results.append({'error': str(e)[:200]})
    return jsonify(results)
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
        if path.startswith('api/') or path.startswith('auth/') or path.startswith('static/') or path.startswith('debug/'):
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
    add_column('users', 'company_id', 'INTEGER')

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

    def safe_fix_column(table, column, target_type):
        try:
            cols = [c for c in inspector.get_columns(table) if c['name'] == column]
            if not cols:
                return
            current = str(cols[0]['type']).upper()
            target_upper = target_type.upper()
            type_map = {
                'VARCHAR': ['FLOAT', 'DOUBLE', 'NUMERIC', 'INT', 'TEXT', 'BOOLEAN'],
                'TEXT': ['FLOAT', 'DOUBLE', 'NUMERIC', 'INT', 'BOOLEAN'],
                'TIMESTAMP': ['FLOAT', 'DOUBLE', 'NUMERIC', 'INT'],
                'INTEGER': ['FLOAT', 'DOUBLE', 'NUMERIC'],
                'FLOAT': ['INT', 'BIGINT'],
            }
            wrong_from = type_map.get(target_upper.split('(')[0].split(' ')[0], [])
            needs_fix = any(t in current for t in wrong_from)
            if not needs_fix:
                return
            if 'TIMESTAMP' in target_upper:
                db.session.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT'))
                db.session.execute(sa.text(f'UPDATE {table} SET {column} = NULL'))
                db.session.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type}'))
            else:
                db.session.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type} USING {column}::text::{target_type.lower()}"))
            db.session.commit()
            print(f"  ~ fixed {table}.{column}: {current} -> {target_type}")
        except Exception as e:
            db.session.rollback()
            msg = str(e).lower()
            if 'already' not in msg and 'does not exist' not in msg:
                print(f"  ! fix {table}.{column}: {e}")

    safe_fix_column('employees', 'worker_type', 'VARCHAR(20)')
    safe_fix_column('employees', 'employee_type', 'VARCHAR(20)')
    safe_fix_column('employees', 'allowances_updated_at', 'TIMESTAMP')
    safe_fix_column('employees', 'region', 'VARCHAR(100)')
    safe_fix_column('employees', 'phone', 'VARCHAR(20)')
    safe_fix_column('employees', 'job_title', 'VARCHAR(100)')
    safe_fix_column('employees', 'name', 'VARCHAR(100)')
    safe_fix_column('employees', 'card_number', 'VARCHAR(20)')
    safe_fix_column('employees', 'code', 'VARCHAR(20)')

    def fix_all_numeric_string_columns(table, columns_and_types):
        for col_name, col_type in columns_and_types:
            safe_fix_column(table, col_name, col_type)

    def raw_fix_column(table, column, target_type):
        try:
            row = db.session.execute(sa.text(
                f"SELECT data_type FROM information_schema.columns "
                f"WHERE table_name = '{table}' AND column_name = '{column}'"
            )).fetchone()
            if not row:
                return
            current = row[0]
            target_lower = target_type.lower().split('(')[0].strip()
            if current == target_lower or (current in ('character varying','varchar') and 'varchar' in target_lower):
                return
            print(f"  raw fix: {table}.{column} is {current}, changing to {target_type}")
            if 'timestamp' in target_lower:
                db.session.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT'))
                db.session.execute(sa.text(f'UPDATE {table} SET {column} = NULL'))
                db.session.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type}'))
            elif 'varchar' in target_lower or 'text' in target_lower:
                db.session.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type} USING {column}::text"))
            else:
                db.session.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type}'))
            db.session.commit()
            print(f"  raw fix: {table}.{column} -> {target_type} OK")
        except Exception as e:
            db.session.rollback()
            print(f"  raw fix: {table}.{column} -> {e}")

    raw_fix_column('employees', 'allowances_updated_at', 'TIMESTAMP')
    raw_fix_column('employees', 'worker_type', 'VARCHAR(20)')
    raw_fix_column('employees', 'employee_type', 'VARCHAR(20)')

    try:
        raw_cols = db.session.execute(sa.text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'employees' ORDER BY ordinal_position"
        )).fetchall()
        print(f"  employees columns: {[(c[0], c[1]) for c in raw_cols]}")
    except Exception as e:
        print(f"  ! could not inspect columns: {e}")

    try:
        table_columns = {
            'financial_transactions': [
                ('description', 'VARCHAR(200)'), ('reference', 'VARCHAR(50)'),
                ('payment_method', 'VARCHAR(20)'), ('settled_amount', 'FLOAT'),
            ],
            'accounts': [
                ('code', 'VARCHAR(20)'), ('name_ar', 'VARCHAR(100)'),
                ('name_en', 'VARCHAR(100)'), ('nature', 'VARCHAR(10)'),
                ('account_type', 'VARCHAR(20)'),
            ],
            'journal_entries': [
                ('description', 'VARCHAR(200)'), ('reference_type', 'VARCHAR(50)'),
                ('reference_id', 'INTEGER'),
            ],
            'suppliers': [
                ('name', 'VARCHAR(100)'), ('phone', 'VARCHAR(20)'),
                ('email', 'VARCHAR(100)'), ('address', 'VARCHAR(200)'),
                ('contact_person', 'VARCHAR(100)'), ('supplier_type', 'VARCHAR(20)'),
                ('code', 'VARCHAR(20)'),
            ],
            'companies': [
                ('name', 'VARCHAR(100)'), ('phone', 'VARCHAR(20)'),
                ('email', 'VARCHAR(100)'), ('address', 'VARCHAR(200)'),
                ('contact_person', 'VARCHAR(100)'), ('code', 'VARCHAR(20)'),
            ],
            'users': [
                ('username', 'VARCHAR(50)'), ('role', 'VARCHAR(20)'),
                ('allowed_pages', 'TEXT'),
            ],
            'salaries': [
                ('month', 'VARCHAR(10)'), ('status', 'VARCHAR(20)'),
                ('notes', 'TEXT'),
            ],
            'evaluations': [
                ('evaluation_type', 'VARCHAR(20)'), ('notes', 'TEXT'),
                ('period', 'VARCHAR(10)'),
            ],
            'attendance': [
                ('status', 'VARCHAR(20)'), ('notes', 'TEXT'),
            ],
            'leave_requests': [
                ('status', 'VARCHAR(20)'), ('reason', 'TEXT'),
                ('response_note', 'TEXT'), ('leave_type', 'VARCHAR(20)'),
            ],
            'work_plans': [
                ('title', 'VARCHAR(100)'), ('description', 'TEXT'),
                ('status', 'VARCHAR(20)'), ('period', 'VARCHAR(20)'),
            ],
            'work_plan_tasks': [
                ('title', 'VARCHAR(100)'), ('description', 'TEXT'),
                ('status', 'VARCHAR(20)'), ('assigned_to', 'VARCHAR(50)'),
            ],
            'bank_info': [
                ('bank_name', 'VARCHAR(100)'), ('account_number', 'VARCHAR(30)'),
                ('iban', 'VARCHAR(30)'), ('swift_code', 'VARCHAR(20)'),
                ('branch_name', 'VARCHAR(100)'), ('account_type', 'VARCHAR(20)'),
                ('currency', 'VARCHAR(10)'), ('notes', 'TEXT'),
            ],
            'supplier_invoices': [
                ('invoice_number', 'VARCHAR(50)'), ('description', 'TEXT'),
                ('status', 'VARCHAR(20)'), ('invoice_type', 'VARCHAR(20)'),
            ],
        }
        existing = set(inspector.get_table_names())
        for tname, cols in table_columns.items():
            if tname in existing:
                fix_all_numeric_string_columns(tname, cols)
    except Exception as e:
        print(f"  ! fix all columns error: {e}")

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
