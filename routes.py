# routes.py
from models import ExpenseCategory
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import func
from weasyprint import HTML
from utils import (
    role_required,calculate_worker_salary_breakdown, print_salary_breakdown,
    get_financial_month_dates,
    format_currency,
    get_regions,
    get_employee_attendance_summary,
    get_employee_overtime_hours,
    get_employee_daily_allowance,
    get_current_month_preparation,
    get_status_badge_class,
    get_status_text_ar,
    ensure_accounts_exist,
    auto_close_expenses,
    redistribute_expenses,
    create_journal_entry,
    create_salary_journal_entry,
    create_salary_payment_journal_entry,
    create_transaction_journal_entry,
    create_contract_journal_entry,
    create_customer_invoice_journal_entry,
    create_customer_payment_journal_entry,
    create_invoice_journal_entry,
    create_invoice_payment_journal_entry,
    create_supplier_invoice_journal_entry,
    create_supplier_invoice_payment_journal_entry,
    create_company_payment_journal_entry,
    create_expense_invoice_journal_entry,
    create_expense_payment_journal_entry,
    reverse_journal_entry,
    reverse_invoice_journal_entry,
    get_next_entry_number,
    create_salary_accrual,
    refresh_all_reports,
    calculate_worker_salary_breakdown,
    print_salary_breakdown
)

from config import Config
from models import (
db, User, Employee, Attendance, FinancialTransaction, Salary,
Evaluation, Company, Contract, Invoice, Location, Region,
EvaluationCriteria, AttendancePreparation,
AttendancePreparationDetail,
AttendancePeriodTransfer,           # ✅ تأكد من وجودها
AttendancePeriodTransferDetail,     # ✅ تأكد من وجودها
AreaEvaluationCriteria,
AreaEvaluation, Account, TrialBalance, FiscalYear,
AccountBalance, JournalEntryDetail, JournalEntry,
CompanyPayment, Supplier, ExpenseCategory, SupplierInvoice,
SupplierInvoicePayment
)

def register_routes(app):
    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            return render_template('landing.html')
        try:
            today = datetime.now().date()
            total_employees = Employee.query.filter_by(is_active=True).count()
            today_attendance = Attendance.query.filter_by(date=today, attendance_status='present').count()
            pending_transactions = FinancialTransaction.query.filter_by(is_settled=False).count()
            pending_salaries = Salary.query.filter_by(is_paid=False).count()
            stats = {
                'total_employees': total_employees,
                'today_attendance': today_attendance,
                'pending_transactions': pending_transactions,
                'pending_salaries': pending_salaries
            }
            recent_attendance = Attendance.query.filter(Attendance.attendance_status == 'present').order_by(
                Attendance.date.desc()).limit(5).all()

            # بيانات الرواتب للرسم البياني
            salaries_data = []
            for i in range(6):
                date = datetime.now() - timedelta(days=30 * i)
                month_year = date.strftime('%m-%Y')
                total = db.session.query(func.sum(Salary.total_salary)).filter_by(month_year=month_year).scalar() or 0
                salaries_data.append({'month': date.strftime('%b'), 'total': float(total)})

            # بيانات المناطق
            regions_result = db.session.query(
                Employee.region,
                db.func.count(Employee.id).label('count')
            ).filter(
                Employee.is_active == True,
                Employee.region != None,
                Employee.region != ''
            ).group_by(Employee.region).all()

            regions_data = []
            for row in regions_result:
                if row[0]:
                    regions_data.append({
                        'region': row[0],
                        'count': row[1]
                    })

            return render_template('index.html',
                                   stats=stats,
                                   recent_attendance=recent_attendance,
                                   salaries_data=salaries_data,
                                   regions_data=regions_data,
                                   now=datetime.now())
        except Exception as e:
            print(f"Error in index: {e}")
            import traceback
            traceback.print_exc()
            return render_template('index.html',
                                   stats={'total_employees': 0, 'today_attendance': 0, 'pending_transactions': 0,
                                          'pending_salaries': 0},
                                   recent_attendance=[],
                                   salaries_data=[],
                                   regions_data=[],
                                   now=datetime.now())

    # استيراد دوال utils بشكل منفصل
    # ==================== المصادقة ====================
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')


            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                login_user(user)
                flash('تم تسجيل الدخول بنجاح', 'success')
                return redirect(url_for('index'))
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('تم تسجيل الخروج بنجاح', 'success')
        return redirect(url_for('login'))

    # ==================== إدارة المستخدمين ====================
    @app.route('/users')
    @login_required
    @role_required('admin')
    def users_list():
        users = User.query.all()
        return render_template('users/users.html', users=users)

    @app.route('/users/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def add_user():
        if request.method == 'POST':
            username = request.form.get('username')
            if User.query.filter_by(username=username).first():
                flash('اسم المستخدم موجود مسبقاً', 'danger')
                return redirect(url_for('add_user'))

            user = User(
                username=username,
                password=generate_password_hash(request.form.get('password')),
                full_name=request.form.get('full_name'),
                role=request.form.get('role')
            )
            db.session.add(user)
            db.session.commit()
            flash('تم إضافة المستخدم بنجاح', 'success')
            return redirect(url_for('users_list'))
        return render_template('users/add_user.html', roles=Config.ROLES)

    @app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def edit_user(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            user.full_name = request.form.get('full_name')
            user.role = request.form.get('role')
            if request.form.get('password'):
                user.password = generate_password_hash(request.form.get('password'))
            db.session.commit()
            flash('تم تحديث المستخدم بنجاح', 'success')
            return redirect(url_for('users_list'))

        roles = {
            'admin': 'مدير النظام',
            'supervisor': 'مشرف',
            'finance': 'موظف مالي',
            'viewer': 'مشاهد'
        }
        return render_template('users/edit_user.html', user=user, roles=roles)

    @app.route('/users/delete/<int:user_id>')
    @login_required
    @role_required('admin')
    def delete_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('لا يمكن حذف المستخدم الحالي', 'danger')
        else:
            db.session.delete(user)
            db.session.commit()
            flash('تم حذف المستخدم بنجاح', 'success')
        return redirect(url_for('users_list'))

    from flask import request, jsonify

    @app.route('/check-username')
    def check_username():
        username = request.args.get('username')

        exists = User.query.filter_by(username=username).first() is not None

        return jsonify({
            "exists": exists
        })

    # ==================== إدارة الموظفين ====================
    # ==================== إدارة الموظفين ====================

    def get_supervisor_workers():
        """الحصول على العمال التابعين للمشرف الحالي"""
        if current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id, is_active=True).first()
            if supervisor_employee:
                return Employee.query.filter(
                    Employee.is_active == True,
                    Employee.supervisor_id == supervisor_employee.id
                ).all()
        return []

    def can_edit_employee(employee):
        """التحقق من صلاحية تعديل الموظف"""
        if current_user.role == 'admin':
            return True
        elif current_user.role == 'supervisor':
            # المشرف لا يمكنه تعديل أي موظف
            return False
        return False

    def can_delete_employee(employee):
        """التحقق من صلاحية حذف الموظف"""
        if current_user.role == 'admin':
            return True
        return False

    @app.route('/employees')
    @login_required
    def employees_list():
        from sqlalchemy.orm import joinedload

        # تحديد الموظفين حسب صلاحية المستخدم
        if current_user.role == 'admin':
            employees = Employee.query.options(
                joinedload(Employee.employee_company),
                joinedload(Employee.supervisor)
            ).filter_by(is_active=True).all()
        elif current_user.role == 'supervisor':
            # المشرف يرى فقط العمال التابعين له
            employees = get_supervisor_workers()
        else:
            employees = []

        regions = get_regions()
        companies = Company.query.all()

        # تمرير صلاحية التعديل والحذف إلى القالب
        return render_template('employees/employees.html',
                               employees=employees,
                               regions=regions,
                               companies=companies,
                               can_edit=(current_user.role == 'admin'),
                               can_delete=(current_user.role == 'admin'))

    @app.route('/employees/import', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')  # ✅ فقط المدير يمكنه استيراد الموظفين
    def import_employees():
        if request.method == 'POST':
            file = request.files.get('file')
            if file and file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
                count = 0
                for _, row in df.iterrows():
                    if pd.notna(row.get('الاســــــم')) and pd.notna(row.get('رقم البطاقة')):
                        company_name = row.get('الشركة', '')
                        company = None
                        if company_name:
                            company = Company.query.filter_by(name=company_name).first()

                        employee = Employee(
                            name=row['الاســــــم'],
                            card_number=str(row['رقم البطاقة']),
                            code=str(row.get('كود تعريف', '')),
                            job_title=row.get('الوظيفة', ''),
                            region=row.get('المنطقة', ''),
                            is_resident=row.get('ميزة ساكن') == 'ساكن' if pd.notna(row.get('ميزة ساكن')) else False,
                            phone=str(row.get('رقم الجوال', '')),
                            salary=float(row.get('الراتب', 60000)),
                            company_id=company.id if company else None
                        )
                        db.session.add(employee)
                        count += 1
                db.session.commit()
                flash(f'تم استيراد {count} موظف بنجاح', 'success')
                return redirect(url_for('employees_list'))
            flash('الرجاء اختيار ملف Excel صحيح', 'danger')

        companies = Company.query.all()
        return render_template('employees/import_employees.html', companies=companies)

    @app.route('/employees/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')  # ✅ فقط المدير يمكنه إضافة موظفين
    def add_employee():
        if request.method == 'POST':
            card_number = request.form.get('card_number')
            code = request.form.get('code')
            employee_type = request.form.get('employee_type')
            supervisor_id = request.form.get('supervisor_id')

            if Employee.query.filter_by(card_number=card_number).first():
                flash('رقم البطاقة موجود مسبقاً', 'danger')
            elif Employee.query.filter_by(code=code).first():
                flash('كود التعريف موجود مسبقاً', 'danger')
            else:
                employee = Employee(
                    name=request.form.get('full_name'),
                    card_number=card_number,
                    code=code,
                    job_title=request.form.get('job_title'),
                    region=request.form.get('region'),
                    is_resident=request.form.get('is_resident') == 'on',
                    phone=request.form.get('phone'),
                    salary=float(request.form.get('salary', 60000)),
                    company_id=request.form.get('company_id') or None,
                    employee_type=employee_type
                )
                if employee_type == 'worker' and supervisor_id:
                    employee.supervisor_id = supervisor_id

                db.session.add(employee)
                db.session.commit()

                if employee_type in ['supervisor', 'admin']:
                    username = request.form.get('username')
                    password = request.form.get('password')
                    if User.query.filter_by(username=username).first():
                        flash('اسم المستخدم موجود مسبقاً', 'danger')
                        db.session.delete(employee)
                        db.session.commit()
                    else:
                        role = 'admin' if employee_type == 'admin' else 'supervisor'
                        user = User(
                            username=username,
                            password=generate_password_hash(password),
                            full_name=request.form.get('full_name'),
                            role=role
                        )
                        db.session.add(user)
                        db.session.commit()
                        employee.user_id = user.id
                        db.session.commit()
                        flash(f'تم إضافة {("المدير" if employee_type == "admin" else "المشرف")} وحساب المستخدم بنجاح',
                              'success')
                else:
                    flash('تم إضافة الموظف (عامل زراعة) بنجاح', 'success')

                return redirect(url_for('employees_list'))

        companies = Company.query.all()
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]

        supervisors = Employee.query.filter(
            (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
            Employee.is_active == True
        ).all()

        supervisors_data = [{
            'id': s.id,
            'name': s.name,
            'job_title': s.job_title,
            'company_id': s.company_id
        } for s in supervisors]

        return render_template('employees/add_employee.html',
                               companies=companies_data,
                               supervisors=supervisors_data)

    @app.route('/employees/edit/<int:emp_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')  # ✅ فقط المدير يمكنه تعديل الموظفين
    def edit_employee(emp_id):
        employee = Employee.query.get_or_404(emp_id)
        old_employee_type = employee.employee_type
        old_supervisor_id = employee.supervisor_id

        if request.method == 'POST':
            card_number = request.form.get('card_number')
            code = request.form.get('code')
            employee_type = request.form.get('employee_type')
            supervisor_id = request.form.get('supervisor_id')

            existing_card = Employee.query.filter(
                Employee.card_number == card_number,
                Employee.id != emp_id
            ).first()
            if existing_card:
                flash('رقم البطاقة موجود مسبقاً لمستخدم آخر', 'danger')
                companies = Company.query.all()
                supervisors = Employee.query.filter(
                    (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
                    Employee.is_active == True,
                    Employee.id != emp_id
                ).all()
                supervisors_data = [{'id': s.id, 'name': s.name, 'job_title': s.job_title, 'company_id': s.company_id}
                                    for s in supervisors]
                return render_template('employees/edit_employee.html',
                                       employee=employee,
                                       companies=companies,
                                       supervisors=supervisors_data)

            existing_code = Employee.query.filter(
                Employee.code == code,
                Employee.id != emp_id
            ).first()
            if existing_code:
                flash('كود التعريف موجود مسبقاً لمستخدم آخر', 'danger')
                companies = Company.query.all()
                supervisors = Employee.query.filter(
                    (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
                    Employee.is_active == True,
                    Employee.id != emp_id
                ).all()
                supervisors_data = [{'id': s.id, 'name': s.name, 'job_title': s.job_title, 'company_id': s.company_id}
                                    for s in supervisors]
                return render_template('employees/edit_employee.html',
                                       employee=employee,
                                       companies=companies,
                                       supervisors=supervisors_data)

            employee.name = request.form.get('full_name')
            employee.card_number = card_number
            employee.code = code
            employee.job_title = request.form.get('job_title')
            employee.region = request.form.get('region')
            employee.is_resident = request.form.get('is_resident') == 'on'
            employee.phone = request.form.get('phone')
            employee.salary = float(request.form.get('salary', 60000))
            employee.company_id = request.form.get('company_id') or None
            employee.employee_type = employee_type

            if employee_type == 'worker' and supervisor_id:
                employee.supervisor_id = supervisor_id
            elif employee_type != 'worker':
                employee.supervisor_id = None

            if old_employee_type in ['supervisor', 'admin'] and employee_type == 'worker':
                if employee.user_id:
                    user = User.query.get(employee.user_id)
                    if user:
                        db.session.delete(user)
                    employee.user_id = None

            elif old_employee_type == 'worker' and employee_type in ['supervisor', 'admin']:
                username = request.form.get('username')
                password = request.form.get('password')

                if username and password:
                    if User.query.filter_by(username=username).first():
                        flash('اسم المستخدم موجود مسبقاً', 'danger')
                        companies = Company.query.all()
                        supervisors = Employee.query.filter(
                            (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
                            Employee.is_active == True,
                            Employee.id != emp_id
                        ).all()
                        supervisors_data = [
                            {'id': s.id, 'name': s.name, 'job_title': s.job_title, 'company_id': s.company_id} for s in
                            supervisors]
                        return render_template('employees/edit_employee.html',
                                               employee=employee,
                                               companies=companies,
                                               supervisors=supervisors_data)

                    role = 'admin' if employee_type == 'admin' else 'supervisor'
                    user = User(
                        username=username,
                        password=generate_password_hash(password),
                        full_name=employee.name,
                        role=role
                    )
                    db.session.add(user)
                    db.session.commit()
                    employee.user_id = user.id

            elif employee_type in ['supervisor', 'admin'] and employee.user_id:
                username = request.form.get('username')
                password = request.form.get('password')

                if username:
                    existing_user = User.query.filter(
                        User.username == username,
                        User.id != employee.user_id
                    ).first()
                    if existing_user:
                        flash('اسم المستخدم موجود مسبقاً', 'danger')
                        companies = Company.query.all()
                        supervisors = Employee.query.filter(
                            (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
                            Employee.is_active == True,
                            Employee.id != emp_id
                        ).all()
                        supervisors_data = [
                            {'id': s.id, 'name': s.name, 'job_title': s.job_title, 'company_id': s.company_id} for s in
                            supervisors]
                        return render_template('employees/edit_employee.html',
                                               employee=employee,
                                               companies=companies,
                                               supervisors=supervisors_data)

                    user = User.query.get(employee.user_id)
                    user.username = username
                    if password and len(password) >= 6:
                        user.password = generate_password_hash(password)
                    db.session.commit()

            db.session.commit()

            if employee_type in ['supervisor', 'admin']:
                flash(f'تم تحديث بيانات {("المدير" if employee_type == "admin" else "المشرف")} بنجاح', 'success')
            else:
                flash('تم تحديث بيانات الموظف بنجاح', 'success')

            return redirect(url_for('employees_list'))

        companies = Company.query.all()
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]

        supervisors = Employee.query.filter(
            (Employee.job_title.contains('مشرف')) | (Employee.job_title == 'إداري'),
            Employee.is_active == True,
            Employee.id != emp_id
        ).all()

        supervisors_data = [{
            'id': s.id,
            'name': s.name,
            'job_title': s.job_title,
            'company_id': s.company_id
        } for s in supervisors]

        user_data = None
        if employee.user_id:
            user = User.query.get(employee.user_id)
            if user:
                user_data = {
                    'username': user.username,
                    'role': user.role
                }

        return render_template('employees/edit_employee.html',
                               employee=employee,
                               companies=companies_data,
                               supervisors=supervisors_data,
                               user_data=user_data,
                               now=datetime.now())

    @app.route('/employees/delete/<int:emp_id>')
    @login_required
    @role_required('admin')  # ✅ فقط المدير يمكنه حذف الموظفين
    def delete_employee(emp_id):
        employee = Employee.query.get_or_404(emp_id)
        employee.is_active = False
        db.session.commit()
        flash('تم حذف الموظف بنجاح', 'success')
        return redirect(url_for('employees_list'))



    @app.route('/api/areas/<int:company_id>')
    @login_required
    def get_areas_by_company(company_id):
        areas = Region.query.filter_by(company_id=company_id).all()
        return jsonify({'success': True, 'data': [{'id': a.id, 'name': a.name} for a in areas]})

    @app.route('/api/locations/<int:area_id>')
    @login_required
    def get_locations_by_area(area_id):
        locations = Location.query.filter_by(region_id=area_id).all()
        return jsonify({'success': True, 'data': [{'id': l.id, 'name': l.name} for l in locations]})

    @app.route('/employees/api/list')
    @login_required
    def employees_api():
        employees = Employee.query.filter_by(is_active=True).all()
        return jsonify([e.to_dict() for e in employees])

    @app.route('/employees/api/company/<int:company_id>')
    @login_required
    def employees_by_company_api(company_id):
        employees = Employee.query.filter_by(is_active=True, company_id=company_id).all()
        return jsonify([e.to_dict() for e in employees])

    @app.route('/employees/check_card', methods=['POST'])
    @login_required
    def check_card_number():
        """التحقق من توفر رقم البطاقة"""
        data = request.get_json()
        card_number = data.get('card_number')
        employee_id = data.get('employee_id')

        query = Employee.query.filter_by(card_number=card_number)
        if employee_id:
            query = query.filter(Employee.id != employee_id)

        exists = query.first() is not None
        return jsonify({'exists': exists})

    @app.route('/employees/check_code', methods=['POST'])
    @login_required
    def check_employee_code():
        """التحقق من توفر كود التعريف"""
        data = request.get_json()
        code = data.get('code')
        employee_id = data.get('employee_id')

        query = Employee.query.filter_by(code=code)
        if employee_id:
            query = query.filter(Employee.id != employee_id)

        exists = query.first() is not None
        return jsonify({'exists': exists})
    # ==================== الحضور والانصراف ====================
    # ==================== الحضور والانصراف ====================
    @app.route('/attendance')
    @login_required
    def attendance_list():
        today = datetime.now().date()
        date = request.args.get('date', today.strftime('%Y-%m-%d'))
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()

        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)

        # جلب بيانات الحضور
        attendances = Attendance.query.filter_by(date=selected_date).all()
        attendance_dict = {a.employee_id: a for a in attendances}

        # جلب الموظفين حسب صلاحية المستخدم
        if current_user.role == 'admin':
            employees = Employee.query.filter_by(is_active=True).all()
        elif current_user.role == 'supervisor':
            # المشرف يرى فقط عمال شركته
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                employees = Employee.query.filter_by(is_active=True, company_id=supervisor_employee.company_id).all()
            else:
                employees = []
        else:
            employees = []

        regions = get_regions()
        companies = Company.query.all()

        return render_template('attendance/attendance.html',
                               attendance_dict=attendance_dict,
                               employees=employees,
                               selected_date=selected_date,
                               prev_date=prev_date.strftime('%Y-%m-%d'),
                               next_date=next_date.strftime('%Y-%m-%d'),
                               today=today.strftime('%Y-%m-%d'),
                               regions=regions,
                               companies=companies)

    # في routes.py، تأكد من وجود هذه الدوال

    @app.route('/attendance/add', methods=['POST'])
    @login_required
    def add_attendance():
        try:
            employee_id = request.form.get('employee_id')
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            attendance_status = request.form.get('attendance_status', 'present')

            # التحقق من وجود الموظف
            employee = Employee.query.get(employee_id)
            if not employee:
                flash('الموظف غير موجود', 'danger')
                return redirect(url_for('attendance_list'))

            # معالجة وقت الدخول
            check_in_time = None
            if request.form.get('check_in_time'):
                check_in_time = datetime.strptime(request.form.get('check_in_time'), '%H:%M').time()

            # معالجة وقت الخروج
            check_out_time = None
            if request.form.get('check_out_time'):
                check_out_time = datetime.strptime(request.form.get('check_out_time'), '%H:%M').time()

            # التحقق من وجود تسجيل سابق
            existing = Attendance.query.filter_by(employee_id=employee_id, date=date).first()

            if existing:
                # تحديث التسجيل الموجود
                existing.attendance_status = attendance_status
                existing.late_minutes = int(request.form.get('late_minutes', 0))
                existing.sick_leave = attendance_status == 'sick'
                existing.sick_leave_days = int(
                    request.form.get('sick_leave_days', 0)) if attendance_status == 'sick' else 0
                existing.check_in_time = check_in_time
                existing.check_out_time = check_out_time
                existing.notes = request.form.get('notes', '')
                flash('تم تحديث الحضور بنجاح', 'success')
            else:
                # إنشاء تسجيل جديد
                attendance = Attendance(
                    employee_id=employee_id,
                    date=date,
                    attendance_type='individual',
                    attendance_status=attendance_status,
                    late_minutes=int(request.form.get('late_minutes', 0)),
                    sick_leave=attendance_status == 'sick',
                    sick_leave_days=int(request.form.get('sick_leave_days', 0)) if attendance_status == 'sick' else 0,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    notes=request.form.get('notes', ''),
                    created_by=current_user.id
                )
                db.session.add(attendance)
                flash('تم تسجيل الحضور بنجاح', 'success')

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            print(f"Error in add_attendance: {e}")

        return redirect(url_for('attendance_list', date=date))

    @app.route('/attendance/remove', methods=['POST'])
    @login_required
    def remove_attendance():
        employee_id = request.form.get('employee_id')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

        attendance = Attendance.query.filter_by(employee_id=employee_id, date=date).first()
        if attendance:
            db.session.delete(attendance)
            db.session.commit()
            flash('تم إزالة الحضور بنجاح', 'success')

        return redirect(url_for('attendance_list', date=date))

    @app.route('/attendance/group', methods=['POST'])
    @login_required
    def group_attendance():
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        company_id = request.form.get('company_id')
        region = request.form.get('region')
        attendance_status = request.form.get('attendance_status', 'present')

        query = Employee.query.filter_by(is_active=True)
        filter_name = ""

        if company_id:
            query = query.filter_by(company_id=company_id)
            company = Company.query.get(company_id)
            filter_name = f"الشركة {company.name if company else ''}"
        elif region:
            query = query.filter_by(region=region)
            filter_name = f"منطقة {region}"
        else:
            flash('الرجاء اختيار شركة أو منطقة', 'danger')
            return redirect(url_for('attendance_list', date=date))

        employees = query.all()
        count = 0

        for employee in employees:
            existing = Attendance.query.filter_by(employee_id=employee.id, date=date).first()
            if not existing:
                attendance = Attendance(
                    employee_id=employee.id,
                    date=date,
                    attendance_type='group',
                    attendance_status=attendance_status,
                    late_minutes=15 if attendance_status == 'late' else 0,
                    sick_leave=attendance_status == 'sick',
                    sick_leave_days=1 if attendance_status == 'sick' else 0,
                    created_by=current_user.id
                )
                db.session.add(attendance)
                count += 1

        db.session.commit()
        flash(f'تم تسجيل الحضور الجماعي لـ {count} موظف في {filter_name}', 'success')
        return redirect(url_for('attendance_list', date=date))

    @app.route('/attendance/edit/<int:attendance_id>', methods=['GET', 'POST'])
    @login_required
    def edit_attendance(attendance_id):
        attendance = Attendance.query.get_or_404(attendance_id)

        if request.method == 'POST':
            attendance.attendance_status = request.form.get('attendance_status')
            attendance.late_minutes = int(request.form.get('late_minutes', 0))

            if request.form.get('check_in_time'):
                attendance.check_in_time = datetime.strptime(request.form.get('check_in_time'), '%H:%M').time()

            if request.form.get('check_out_time'):
                attendance.check_out_time = datetime.strptime(request.form.get('check_out_time'), '%H:%M').time()

            attendance.notes = request.form.get('notes', '')
            db.session.commit()
            flash('تم تحديث الحضور بنجاح', 'success')
            return redirect(url_for('attendance_list', date=attendance.date))

        return render_template('attendance/edit_attendance_a.html', attendance=attendance)

    @app.route('/attendance/bulk_save', methods=['POST'])
    @login_required
    def save_bulk_attendance():
        """حفظ جميع حالات الحضور دفعة واحدة مع دعم الإجازات السنوية"""
        try:
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            employee_ids = request.form.getlist('employee_ids')

            count = 0
            for emp_id in employee_ids:
                status = request.form.get(f'status_{emp_id}')
                employee = Employee.query.get(emp_id)

                if not status or not employee:
                    continue

                # التحقق من وجود تسجيل سابق
                existing = Attendance.query.filter_by(employee_id=emp_id, date=date).first()

                # معالجة حالة الغياب
                if status == 'absent':
                    if existing:
                        db.session.delete(existing)
                    continue

                # معالجة الوقت
                check_in_time = None
                if request.form.get(f'check_in_time_{emp_id}'):
                    check_in_time = datetime.strptime(request.form.get(f'check_in_time_{emp_id}'), '%H:%M').time()

                check_out_time = None
                if request.form.get(f'check_out_time_{emp_id}'):
                    check_out_time = datetime.strptime(request.form.get(f'check_out_time_{emp_id}'), '%H:%M').time()

                # بيانات إضافية حسب الحالة
                late_minutes = int(request.form.get(f'late_minutes_{emp_id}', 0)) if status == 'late' else 0
                sick_leave_days = int(request.form.get(f'sick_leave_days_{emp_id}', 0)) if status == 'sick' else 0

                # معالجة الإجازة السنوية
                annual_leave_days = 0
                days_before = 0

                if status == 'annual_leave_paid':
                    # إجازة سنوية مدفوعة الأجر
                    annual_leave_days = int(request.form.get(f'annual_leave_days_{emp_id}', 1))
                    # تحديث رصيد الإجازات
                    if employee.remaining_annual_leave is None:
                        employee.remaining_annual_leave = 30
                    days_before = employee.remaining_annual_leave
                    employee.remaining_annual_leave -= annual_leave_days
                    status = 'annual_leave'  # حفظ في قاعدة البيانات كـ annual_leave

                elif status == 'annual_leave_unpaid':
                    # إجازة سنوية بدون أجر
                    annual_leave_days = int(request.form.get(f'annual_leave_unpaid_days_{emp_id}', 1))
                    status = 'annual_leave_unpaid'  # نوع مختلف
                else:
                    annual_leave_days = int(
                        request.form.get(f'annual_leave_days_{emp_id}', 0)) if status == 'annual_leave' else 0

                if existing:
                    # تحديث التسجيل الموجود
                    existing.attendance_status = status
                    existing.late_minutes = late_minutes
                    existing.sick_leave = status == 'sick'
                    existing.sick_leave_days = sick_leave_days
                    existing.annual_leave_days = annual_leave_days
                    existing.check_in_time = check_in_time
                    existing.check_out_time = check_out_time
                    existing.notes = request.form.get(f'notes_{emp_id}', '')
                else:
                    # إنشاء تسجيل جديد
                    attendance = Attendance(
                        employee_id=emp_id,
                        date=date,
                        attendance_type='individual',
                        attendance_status=status,
                        late_minutes=late_minutes,
                        sick_leave=status == 'sick',
                        sick_leave_days=sick_leave_days,
                        annual_leave_days=annual_leave_days,
                        check_in_time=check_in_time,
                        check_out_time=check_out_time,
                        notes=request.form.get(f'notes_{emp_id}', ''),
                        created_by=current_user.id
                    )
                    db.session.add(attendance)

                # طباعة معلومات التصحيح للإجازة المدفوعة
                if status == 'annual_leave' and days_before > 0:
                    print(
                        f'📅 {employee.name}: إجازة سنوية مدفوعة {annual_leave_days} يوم (الرصيد السابق: {days_before}, الرصيد الحالي: {employee.remaining_annual_leave})')
                elif status == 'annual_leave_unpaid':
                    print(f'📅 {employee.name}: إجازة سنوية بدون أجر {annual_leave_days} يوم')

                count += 1

            db.session.commit()
            flash(f'تم تسجيل/تحديث حضور {count} موظف بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            print(f"Error in save_bulk_attendance: {e}")

        return redirect(url_for('attendance_list', date=date))

    @app.route('/attendance/period-transfer/create-management')
    @login_required
    @role_required('admin', 'finance')
    def create_management_transfer():
        """إنشاء ترحيل مخصص للمدير والمشرف"""
        from utils import create_management_salary_transfer

        result = create_management_salary_transfer()

        if result['success']:
            flash(f"✅ {result['message']}", 'success')
            flash(f"📋 الفترة: {result['start_date']} إلى {result['end_date']}", 'info')
            for emp in result['employees']:
                flash(f"   👤 {emp['type']}: {emp['name']} - الراتب: {emp['salary']:,.0f} ريال", 'info')
            return redirect(url_for('view_period_transfer', transfer_id=result['transfer_id']))
        else:
            flash(f"❌ {result['message']}", 'danger')
            return redirect(url_for('period_transfer_list'))

    # ==================== ترحيل فترة الدوام إلى الرواتب ====================
    @app.route('/attendance/period-transfer')
    @login_required
    @role_required('admin', 'finance')
    def period_transfer_list():
        """عرض قائمة ترحيلات فترات الدوام"""
        transfers = AttendancePeriodTransfer.query.order_by(AttendancePeriodTransfer.start_date.desc()).all()
        return render_template('attendance/period_transfers_list.html', transfers=transfers)

    @app.route('/attendance/period-transfer/transfer-to-salary/<int:transfer_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def transfer_period_to_salary(transfer_id):
        """ترحيل فترة الدوام إلى الرواتب - حساب الرواتب بناءً على الفترة الكاملة"""
        transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

        if transfer.is_transferred:
            flash('تم ترحيل هذه الفترة مسبقاً', 'danger')
            return redirect(url_for('period_transfer_list'))

        try:
            start_date = transfer.start_date
            end_date = transfer.end_date
            period_name = transfer.period_name
            count = 0

            for detail in transfer.transfers_details:
                employee = detail.employee

                # حساب عدد أيام الفترة الفعلية
                period_days = (end_date - start_date).days + 1
                daily_rate = employee.salary / 30

                # حساب البدل اليومي
                daily_allowance = 0
                if employee.is_resident:
                    daily_rate_allowance = getattr(employee, 'daily_allowance', 500)
                    daily_allowance = detail.attendance_days * daily_rate_allowance

                # حساب الإضافي
                hourly_rate = employee.salary / 30 / 8
                overtime_amount = detail.overtime_hours * (hourly_rate * 1.5)

                # ==================== تعديل مهم: ترحيل المعاملات حسب الفترة فقط ====================
                # جلب المعاملات المالية التي تاريخها ضمن الفترة فقط
                advances = employee.get_transactions_sum('advance', start_date, end_date)
                deductions = employee.get_transactions_sum('deduction', start_date, end_date)
                penalties = employee.get_transactions_sum('penalty', start_date, end_date)
                # في routes.py، عند ترحيل فترة الدوام
                advances = employee.get_transactions_sum('advance', start_date, end_date)
                deductions = employee.get_transactions_sum('deduction', start_date, end_date)
                penalties = employee.get_transactions_sum('penalty', start_date, end_date)
                overtime = employee.get_transactions_sum('overtime', start_date, end_date)

                # أو استخدام الدالة المجمعة
                summary = employee.get_transactions_summary(start_date, end_date)
                advances = summary['advance']
                deductions = summary['deduction']
                penalties = summary['penalty']
                overtime = summary['overtime']
                # ترحيل المعاملات التي تاريخها ضمن الفترة فقط (وليس كل المعاملات)
                for trans in employee.transactions:
                    if not trans.is_settled and start_date <= trans.date <= end_date:
                        trans.is_settled = True
                        trans.settled_date = end_date
                # =====================================================================

                # حساب مبلغ الحضور
                attendance_amount = daily_rate * detail.attendance_days

                # الراتب النهائي
                total_salary = attendance_amount + daily_allowance + overtime_amount - advances - deductions - penalties

                # استخدام الفترة الكاملة كمفتاح
                period_key = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
                period_display = f"فترة من {start_date.strftime('%d/%m/%Y')} إلى {end_date.strftime('%d/%m/%Y')}"

                existing = Salary.query.filter_by(
                    employee_id=employee.id,
                    month_year=period_key
                ).first()

                if existing:
                    existing.attendance_days = detail.attendance_days
                    existing.attendance_amount = attendance_amount
                    existing.overtime_amount = overtime_amount
                    existing.daily_allowance_amount = daily_allowance
                    existing.advance_amount = advances
                    existing.deduction_amount = deductions
                    existing.penalty_amount = penalties
                    existing.total_salary = total_salary
                    existing.notes = period_display
                else:
                    salary = Salary(
                        employee_id=employee.id,
                        month_year=period_key,
                        base_salary=employee.salary,
                        attendance_days=detail.attendance_days,
                        attendance_amount=attendance_amount,
                        daily_allowance_amount=daily_allowance,
                        overtime_amount=overtime_amount,
                        advance_amount=advances,
                        deduction_amount=deductions,
                        penalty_amount=penalties,
                        total_salary=total_salary,
                        notes=period_display
                    )
                    db.session.add(salary)

                detail.is_processed = True
                count += 1

            transfer.is_transferred = True
            transfer.transfer_date = datetime.now().date()
            db.session.commit()

            flash(f'✅ تم ترحيل {count} موظف إلى الرواتب للفترة "{period_name}" من {start_date} إلى {end_date}',
                  'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الترحيل: {str(e)}', 'danger')

        return redirect(url_for('period_transfer_list'))

    @app.route('/attendance/period-transfer/refresh/<int:transfer_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def refresh_period_transfer(transfer_id):
        """تحديث فترة ترحيل موجودة - إعادة حساب بيانات الحضور والإضافي"""
        transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

        if transfer.is_transferred:
            flash('⚠️ لا يمكن تحديث فترة تم ترحيلها بالفعل', 'danger')
            return redirect(url_for('period_transfer_list'))

        try:
            start_date = transfer.start_date
            end_date = transfer.end_date

            # حذف التفاصيل القديمة
            for detail in transfer.transfers_details:
                db.session.delete(detail)

            # جلب الموظفين حسب الفلتر
            query = Employee.query.filter_by(is_active=True)

            if transfer.company_id:
                query = query.filter_by(company_id=transfer.company_id)
                filter_desc = f"شركة {transfer.company.name if transfer.company else ''}"
            elif transfer.region:
                query = query.filter_by(region=transfer.region)
                filter_desc = f"منطقة {transfer.region}"
            else:
                query = query.filter(Employee.employee_type == 'worker')
                filter_desc = "جميع العمال"

            employees = query.all()

            if not employees:
                flash('لا يوجد موظفين في هذا الفلتر', 'warning')
                return redirect(url_for('period_transfer_list'))

            count = 0
            for employee in employees:
                attendance_summary = get_employee_attendance_summary(employee, start_date, end_date)
                overtime_hours = get_employee_overtime_hours(employee, start_date, end_date)

                detail = AttendancePeriodTransferDetail(
                    transfer_id=transfer.id,
                    employee_id=employee.id,
                    attendance_days=attendance_summary['attendance_days'],
                    absent_days=attendance_summary['absent_days'],
                    sick_days=attendance_summary['sick_days'],
                    late_minutes_total=attendance_summary['late_minutes_total'],
                    overtime_hours=overtime_hours
                )
                db.session.add(detail)
                count += 1

            db.session.commit()

            flash(f'✅ تم تحديث فترة "{transfer.period_name}" بنجاح - {count} موظف', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء التحديث: {str(e)}', 'danger')

        return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

    @app.route('/attendance/period-transfer/view/<int:transfer_id>')
    @login_required
    @role_required('admin', 'finance')
    def view_period_transfer(transfer_id):
        """عرض تفاصيل ترحيل فترة الدوام"""
        transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

        # إحصائيات
        total_employees = len(transfer.transfers_details)
        total_attendance_days = sum(d.attendance_days for d in transfer.transfers_details)
        total_overtime_hours = sum(d.overtime_hours for d in transfer.transfers_details)

        stats = {
            'total_employees': total_employees,
            'total_attendance_days': total_attendance_days,
            'total_overtime_hours': total_overtime_hours,
            'processed_count': len([d for d in transfer.transfers_details if d.is_processed])
        }

        return render_template('attendance/view_period_transfer.html',
                               transfer=transfer,
                               details=transfer.transfers_details,
                               stats=stats,
                               now=datetime.now())

    @app.route('/attendance/period-transfer/create', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def create_period_transfer():
        """إنشاء ترحيل فترة دوام جديدة للعمال - يستخرج البيانات من سجلات الحضور اليومية"""
        if request.method == 'POST':
            period_name = request.form.get('period_name')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            company_id = request.form.get('company_id')
            region = request.form.get('region')
            payroll_type = request.form.get('payroll_type', 'labor')  # ✅ إضافة نوع الراتب

            # التحقق من صحة التواريخ
            if start_date > end_date:
                flash('تاريخ البداية يجب أن يكون قبل تاريخ النهاية', 'danger')
                return redirect(url_for('create_period_transfer'))

            # ==================== التحقق من عدم تداخل الفترات ====================
            query = AttendancePeriodTransfer.query.filter(
                AttendancePeriodTransfer.payroll_type == payroll_type,  # ✅ نفس نوع الراتب
                AttendancePeriodTransfer.start_date <= end_date,
                AttendancePeriodTransfer.end_date >= start_date
            )

            # تطبيق نفس الفلتر (شركة أو منطقة)
            if company_id:
                existing = query.filter(AttendancePeriodTransfer.company_id == company_id).first()
                if existing:
                    flash(
                        f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لنفس الشركة من {existing.start_date} إلى {existing.end_date}',
                        'danger')
                    return redirect(url_for('create_period_transfer'))
            elif region:
                existing = query.filter(AttendancePeriodTransfer.region == region).first()
                if existing:
                    flash(
                        f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لنفس المنطقة من {existing.start_date} إلى {existing.end_date}',
                        'danger')
                    return redirect(url_for('create_period_transfer'))
            else:
                existing = query.filter(
                    AttendancePeriodTransfer.company_id == None,
                    AttendancePeriodTransfer.region == None
                ).first()
                if existing:
                    flash(
                        f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لجميع الموظفين من {existing.start_date} إلى {existing.end_date}',
                        'danger')
                    return redirect(url_for('create_period_transfer'))

            # إنشاء ترحيل جديد
            transfer = AttendancePeriodTransfer(
                period_name=period_name,
                payroll_type=payroll_type,  # ✅ تحديد نوع الراتب
                start_date=start_date,
                end_date=end_date,
                transfer_date=datetime.now().date(),
                transferred_by=current_user.id,
                company_id=company_id if company_id else None,
                region=region if region else None
            )
            db.session.add(transfer)
            db.session.commit()

            # جلب الموظفين حسب الفلتر ونوع الراتب
            query = Employee.query.filter_by(is_active=True)

            if payroll_type == 'admin':
                # إدارة: admin, supervisor
                query = query.filter(Employee.employee_type.in_(['admin', 'supervisor']))
            else:
                # عمال: worker فقط
                query = query.filter(Employee.employee_type == 'worker')

            if company_id:
                query = query.filter_by(company_id=company_id)
                filter_desc = f"شركة {Company.query.get(company_id).name if company_id else ''}"
            elif region:
                query = query.filter_by(region=region)
                filter_desc = f"منطقة {region}"
            else:
                filter_desc = "جميع الموظفين"

            employees = query.all()

            if not employees:
                flash('لا يوجد موظفين في هذا الفلتر', 'warning')
                db.session.delete(transfer)
                db.session.commit()
                return redirect(url_for('create_period_transfer'))

            count = 0
            for employee in employees:
                # استخراج إحصائيات الحضور من سجلات الحضور اليومية
                attendance_summary = get_employee_attendance_summary(employee, start_date, end_date)
                overtime_hours = get_employee_overtime_hours(employee, start_date, end_date)

                detail = AttendancePeriodTransferDetail(
                    transfer_id=transfer.id,
                    employee_id=employee.id,
                    attendance_days=attendance_summary['attendance_days'],
                    absent_days=attendance_summary['absent_days'],
                    sick_days=attendance_summary['sick_days'],
                    late_minutes_total=attendance_summary['late_minutes_total'],
                    overtime_hours=overtime_hours
                )
                db.session.add(detail)
                count += 1

            db.session.commit()

            flash(f'✅ تم إنشاء ترحيل فترة الدوام لـ {count} موظف في {filter_desc} من {start_date} إلى {end_date}',
                  'success')
            return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

        # GET request
        companies = Company.query.all()
        regions = get_regions()

        # اقتراح تواريخ تلقائية (من 26 الشهر السابق إلى 25 الشهر الحالي)
        today = datetime.now().date()
        if today.day >= 26:
            start_date = datetime(today.year, today.month, 26).date()
            if today.month == 12:
                end_date = datetime(today.year + 1, 1, 25).date()
            else:
                end_date = datetime(today.year, today.month + 1, 25).date()
        else:
            if today.month == 1:
                start_date = datetime(today.year - 1, 12, 26).date()
            else:
                start_date = datetime(today.year, today.month - 1, 26).date()
            end_date = datetime(today.year, today.month, 25).date()

        return render_template('attendance/create_period_transfer.html',
                               companies=companies,
                               regions=regions,
                               suggested_start_date=start_date,
                               suggested_end_date=end_date)


    # ==================== Company Management Routes ====================
    @app.route('/companies')
    @login_required
    @role_required('admin')  # ✅ فقط المدير يمكنه الوصول إلى قائمة الشركات
    def companies_dashboard():
        """عرض قائمة الشركات"""
        companies = Company.query.all()

        # حساب الإحصائيات باستخدام الأسماء الصحيحة من models.py
        total_regions = 0
        total_locations = 0
        total_employees = 0

        for company in companies:
            total_regions += len(company.company_regions)  # استخدم company_regions
            total_employees += len(company.company_employees)  # استخدم company_employees
            for region in company.company_regions:
                total_locations += len(region.region_locations)  # استخدم region_locations

        stats = {
            'total_companies': len(companies),
            'total_regions': total_regions,
            'total_locations': total_locations,
            'total_employees': total_employees
        }

        return render_template('companies/companies.html', companies=companies, stats=stats)

    @app.route('/companies/<int:company_id>')
    @login_required
    def company_details(company_id):
        """عرض تفاصيل الشركة مع المناطق والمواقع"""
        company = Company.query.get_or_404(company_id)
        return render_template('companies/company_details.html', company=company)

    # إضافة شركة جديدة
    @app.route('/companies/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def add_company():
        if request.method == 'POST':
            existing = Company.query.filter_by(name=request.form.get('name')).first()
            if existing:
                flash('اسم الشركة موجود مسبقاً', 'danger')
                return redirect(url_for('add_company'))

            company = Company(
                name=request.form.get('name'),
                contact_person=request.form.get('contact_person'),
                phone=request.form.get('phone'),
                email=request.form.get('email')
            )
            db.session.add(company)
            db.session.commit()
            flash('تم إضافة الشركة بنجاح', 'success')
            return redirect(url_for('companies_dashboard'))

        return render_template('companies/add_company.html')


    @app.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def edit_company(company_id):
        """تعديل بيانات الشركة"""
        company = Company.query.get_or_404(company_id)

        if request.method == 'POST':
            company.name = request.form.get('name')
            company.contact_person = request.form.get('contact_person')
            company.phone = request.form.get('phone')
            company.email = request.form.get('email')
            db.session.commit()
            flash('تم تحديث بيانات الشركة بنجاح', 'success')
            return redirect(url_for('company_details', company_id=company.id))

        return render_template('companies/edit_company.html', company=company)

    @app.route('/companies/<int:company_id>/delete', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_company(company_id):
        """حذف شركة (مع حذف المناطق والمواقع تلقائياً)"""
        company = Company.query.get_or_404(company_id)
        db.session.delete(company)
        db.session.commit()
        flash('تم حذف الشركة بنجاح', 'success')
        return redirect(url_for('companies_dashboard'))

    # ==================== Region Management Routes ====================
    @app.route('/regions/add', methods=['POST'])
    @login_required
    @role_required('admin')
    def add_region():
        """إضافة منطقة جديدة لشركة"""
        company_id = request.form.get('company_id')
        region_name = request.form.get('region_name')

        # التحقق من عدم وجود نفس المنطقة لنفس الشركة
        existing = Region.query.filter_by(company_id=company_id, name=region_name).first()
        if existing:
            flash('هذه المنطقة موجودة مسبقاً لهذه الشركة', 'danger')
            return redirect(url_for('company_details', company_id=company_id))

        region = Region(
            name=region_name,
            company_id=company_id
        )
        db.session.add(region)
        db.session.commit()
        flash('تم إضافة المنطقة بنجاح', 'success')
        return redirect(url_for('company_details', company_id=company_id))

    @app.route('/regions/<int:region_id>/edit', methods=['POST'])
    @login_required
    @role_required('admin')
    def edit_region(region_id):
        """تعديل اسم المنطقة"""
        region = Region.query.get_or_404(region_id)
        new_name = request.form.get('region_name')

        # التحقق من عدم وجود نفس الاسم لنفس الشركة
        existing = Region.query.filter_by(company_id=region.company_id, name=new_name).first()
        if existing and existing.id != region_id:
            flash('هذا الاسم موجود مسبقاً لهذه الشركة', 'danger')
            return redirect(url_for('company_details', company_id=region.company_id))

        region.name = new_name
        db.session.commit()
        flash('تم تحديث اسم المنطقة بنجاح', 'success')
        return redirect(url_for('company_details', company_id=region.company_id))

    @app.route('/regions/<int:region_id>/delete', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_region(region_id):
        """حذف منطقة (مع حذف المواقع تلقائياً)"""
        region = Region.query.get_or_404(region_id)
        company_id = region.company_id
        db.session.delete(region)
        db.session.commit()
        flash('تم حذف المنطقة بنجاح', 'success')
        return redirect(url_for('company_details', company_id=company_id))

    # ==================== Location Management Routes ====================
    @app.route('/locations/add', methods=['POST'])
    @login_required
    @role_required('admin')
    def add_location():
        """إضافة موقع جديد لمنطقة"""
        region_id = request.form.get('region_id')
        location_name = request.form.get('location_name')
        address = request.form.get('address')
        notes = request.form.get('notes')

        region = Region.query.get_or_404(region_id)

        # التحقق من عدم وجود نفس الموقع لنفس المنطقة
        existing = Location.query.filter_by(region_id=region_id, name=location_name).first()
        if existing:
            flash('هذا الموقع موجود مسبقاً لهذه المنطقة', 'danger')
            return redirect(url_for('company_details', company_id=region.company_id))

        location = Location(
            name=location_name,
            region_id=region_id,
            address=address,
            notes=notes
        )
        db.session.add(location)
        db.session.commit()
        flash('تم إضافة الموقع بنجاح', 'success')
        return redirect(url_for('company_details', company_id=region.company_id))

    @app.route('/locations/<int:location_id>/edit', methods=['POST'])
    @login_required
    @role_required('admin')
    def edit_location(location_id):
        """تعديل بيانات الموقع"""
        location = Location.query.get_or_404(location_id)

        location.name = request.form.get('location_name')
        location.address = request.form.get('address')
        location.notes = request.form.get('notes')

        db.session.commit()
        flash('تم تحديث بيانات الموقع بنجاح', 'success')
        return redirect(url_for('company_details', company_id=location.region.company_id))

    @app.route('/locations/<int:location_id>/delete', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_location(location_id):
        """حذف موقع"""
        location = Location.query.get_or_404(location_id)
        company_id = location.region.company_id
        db.session.delete(location)
        db.session.commit()
        flash('تم حذف الموقع بنجاح', 'success')
        return redirect(url_for('company_details', company_id=company_id))

    # ==================== التقييمات ====================
    @app.route('/evaluations')
    @login_required
    def evaluations_list():
        if current_user.role == 'admin':
            evaluations = Evaluation.query.order_by(Evaluation.date.desc()).all()
        elif current_user.role == 'supervisor':
            # المشرف يرى فقط تقييمات عمال شركته
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                # جلب عمال الشركة
                workers = Employee.query.filter_by(company_id=supervisor_employee.company_id, is_active=True).all()
                worker_ids = [w.id for w in workers]
                evaluations = Evaluation.query.filter(Evaluation.employee_id.in_(worker_ids)).order_by(
                    Evaluation.date.desc()).all()
            else:
                evaluations = []
        else:
            evaluations = []

        return render_template('evaluations/evaluations.html', evaluations=evaluations)

    @app.route('/evaluations/add', methods=['GET', 'POST'])
    @login_required
    def add_evaluation():
        if request.method == 'POST':
            employee_id = request.form.get('employee_id')
            region_id = request.form.get('region_id')
            location_id = request.form.get('location_id')
            comments = request.form.get('comments')
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

            # جمع درجات المعايير
            criteria_scores = []
            total_score = 0
            max_possible = 0

            for key, value in request.form.items():
                if key.startswith('criteria_'):
                    criteria_id = int(key.split('_')[1])
                    score = int(value)

                    criteria = EvaluationCriteria.query.get(criteria_id)
                    if criteria:
                        criteria_scores.append({
                            'criteria_id': criteria_id,
                            'name': criteria.name,
                            'score': score,
                            'max_score': criteria.max_score
                        })
                        total_score += score
                        max_possible += criteria.max_score

            percentage = (total_score / max_possible * 100) if max_possible > 0 else 0

            evaluation = Evaluation(
                employee_id=employee_id,
                evaluator_id=current_user.id,
                evaluation_type='supervisor',
                date=date,
                score=percentage,
                comments=comments,
                region_id=region_id if region_id else None,  # ✅ حفظ المنطقة
                location_id=location_id if location_id else None  # ✅ حفظ الموقع
            )
            evaluation.set_criteria_scores(criteria_scores)
            db.session.add(evaluation)
            db.session.commit()

            flash('تم إضافة التقييم بنجاح', 'success')
            return redirect(url_for('evaluations_list'))

        # جلب البيانات للـ GET
        company_filter = None

        if current_user.role == 'admin':
            employees = Employee.query.filter(
                Employee.is_active == True,
                Employee.employee_type == 'worker'
            ).all()
            companies = Company.query.all()
        elif current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                company_filter = supervisor_employee.company_id
                employees = Employee.query.filter(
                    Employee.is_active == True,
                    Employee.employee_type == 'worker',
                    Employee.company_id == company_filter
                ).all()
                companies = Company.query.filter_by(id=company_filter).all()
            else:
                employees = []
                companies = []
        else:
            employees = []
            companies = []

        # تحويل الموظفين إلى قواميس
        employees_data = [{
            'id': e.id,
            'name': e.name,
            'job_title': e.job_title or 'عامل',
            'company_id': e.company_id,
            'employee_type': e.employee_type
        } for e in employees]

        # جلب المناطق والمواقع
        regions = Region.query.all()
        regions_data = [{'id': r.id, 'name': r.name, 'company_id': r.company_id} for r in regions]

        locations = Location.query.all()
        locations_data = [{
            'id': l.id,
            'name': l.name,
            'region_id': l.region_id,
            'address': l.address or ''
        } for l in locations]

        # جلب المسميات الوظيفية
        job_titles = db.session.query(Employee.job_title).filter(
            Employee.job_title != None,
            Employee.job_title != ''
        ).distinct().all()
        job_titles = [j[0] for j in job_titles if j[0]]

        return render_template('evaluations/add_evaluation.html',
                               employees=employees_data,
                               companies=companies,
                               regions=regions_data,
                               locations=locations_data,
                               job_titles=job_titles,
                               company_filter=company_filter,
                               now=datetime.now())

    @app.route('/api/regions_by_company/<int:company_id>')
    @login_required
    def get_regions_by_company(company_id):
        """API لجلب المناطق حسب الشركة"""
        try:
            regions = Region.query.filter_by(company_id=company_id).all()
            result = [{'id': r.id, 'name': r.name} for r in regions]
            return jsonify(result)
        except Exception as e:
            print(f"Error in get_regions_by_company: {e}")
            return jsonify([])

    @app.route('/api/locations_by_region/<int:region_id>')
    @login_required
    def get_locations_by_region(region_id):
        """API لجلب المواقع حسب المنطقة"""
        try:
            locations = Location.query.filter_by(region_id=region_id).all()
            result = [{'id': l.id, 'name': l.name, 'address': l.address or ''} for l in locations]
            return jsonify(result)
        except Exception as e:
            print(f"Error in get_locations_by_region: {e}")
            return jsonify([])

    # ==================== Evaluation Criteria Management Routes ====================
    @app.route('/api/criteria_by_location/<int:location_id>')
    @login_required
    def get_criteria_by_location(location_id):
        """API لجلب معايير التقييم حسب الموقع"""
        try:
            criteria = EvaluationCriteria.query.filter_by(location_id=location_id, is_active=True).all()
            result = [{'id': c.id, 'name': c.name, 'description': c.description, 'max_score': c.max_score} for c in
                      criteria]
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            print(f"Error in get_criteria_by_location: {e}")
            return jsonify({'success': False, 'data': []})

    # ==================== إدارة معايير التقييم حسب الوظيفة ====================
    @app.route('/evaluation-criteria/add', methods=['GET'])
    @login_required
    @role_required('admin')
    def add_evaluation_criteria_form():
        """عرض نموذج إضافة معيار تقييم"""
        job_titles = db.session.query(Employee.job_title).filter(
            Employee.job_title != None,
            Employee.job_title != ''
        ).distinct().all()
        job_titles = [j[0] for j in job_titles if j[0]]

        return render_template('criteria/add.html', job_titles=job_titles)

    @app.route('/evaluation-criteria/edit/<int:id>', methods=['GET'])
    @login_required
    @role_required('admin')
    def edit_evaluation_criteria_form(id):
        """عرض نموذج تعديل معيار تقييم"""
        criteria = EvaluationCriteria.query.get_or_404(id)

        job_titles = db.session.query(Employee.job_title).filter(
            Employee.job_title != None,
            Employee.job_title != ''
        ).distinct().all()
        job_titles = [j[0] for j in job_titles if j[0]]

        return render_template('criteria/edit.html',
                               criteria=criteria,
                               job_titles=job_titles)

    # ==================== إدارة معايير التقييم (للوظائف) ====================

    @app.route('/evaluation-criteria')
    @login_required
    @role_required('admin')
    def evaluation_criteria_list():
        """عرض جميع معايير التقييم حسب الوظيفة"""
        criteria = EvaluationCriteria.query.filter_by(is_active=True).all()
        job_titles = db.session.query(Employee.job_title).filter(
            Employee.job_title != None,
            Employee.job_title != ''
        ).distinct().all()
        job_titles = [j[0] for j in job_titles if j[0]]

        return render_template('criteria/index.html',
                               criteria=criteria,
                               job_titles=job_titles)

    @app.route('/evaluation-criteria/add', methods=['POST'])
    @login_required
    @role_required('admin')
    def add_evaluation_criteria():
        """إضافة معيار تقييم جديد"""
        try:
            job_title = request.form.get('job_title')
            name = request.form.get('name')
            description = request.form.get('description')
            min_score = int(request.form.get('min_score', 0))
            max_score = int(request.form.get('max_score', 10))

            if min_score >= max_score:
                flash('الحد الأدنى يجب أن يكون أقل من الحد الأقصى', 'danger')
                return redirect(url_for('companies_dashboard'))

            criteria = EvaluationCriteria(
                job_title=job_title,
                name=name,
                description=description,
                min_score=min_score,
                max_score=max_score
            )
            db.session.add(criteria)
            db.session.commit()
            flash(f'تم إضافة معيار "{name}" للوظيفة "{job_title}" بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('companies_dashboard'))

    @app.route('/evaluation-criteria/edit/<int:id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def edit_evaluation_criteria(id):
        """تعديل معيار التقييم"""
        try:
            criteria = EvaluationCriteria.query.get_or_404(id)
            criteria.name = request.form.get('name')
            criteria.description = request.form.get('description')
            criteria.min_score = int(request.form.get('min_score', 0))
            criteria.max_score = int(request.form.get('max_score', 10))

            if criteria.min_score >= criteria.max_score:
                flash('الحد الأدنى يجب أن يكون أقل من الحد الأقصى', 'danger')
                return redirect(url_for('companies_dashboard'))

            db.session.commit()
            flash('تم تحديث معيار التقييم بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('companies_dashboard'))

    @app.route('/evaluation-criteria/delete/<int:id>')
    @login_required
    @role_required('admin')
    def delete_evaluation_criteria(id):
        """حذف معيار التقييم"""
        try:
            criteria = EvaluationCriteria.query.get_or_404(id)
            criteria.is_active = False
            db.session.commit()
            flash('تم حذف معيار التقييم بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('companies_dashboard'))

    @app.route('/api/evaluation-criteria/<int:id>')
    @login_required
    @role_required('admin')
    def get_evaluation_criteria_api(id):
        """API لجلب معيار تقييم واحد للتعديل"""
        criteria = EvaluationCriteria.query.get_or_404(id)
        return jsonify({
            'success': True,
            'id': criteria.id,
            'job_title': criteria.job_title,
            'name': criteria.name,
            'description': criteria.description,
            'min_score': criteria.min_score,
            'max_score': criteria.max_score
        })

    @app.route('/api/criteria-by-job-title')
    @login_required
    def get_criteria_by_job_title():
        """API لجلب معايير التقييم حسب الوظيفة"""
        job_title = request.args.get('job_title')
        if not job_title:
            return jsonify({'success': False, 'data': []})

        criteria = EvaluationCriteria.query.filter_by(
            job_title=job_title,
            is_active=True
        ).all()

        return jsonify({
            'success': True,
            'data': [{
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'min_score': c.min_score,
                'max_score': c.max_score
            } for c in criteria]
        })


    @app.route('/evaluations/add_supervisor', methods=['GET', 'POST'])
    @login_required
    def add_supervisor_evaluation():
        if request.method == 'POST':
            # حساب الدرجة النهائية من المعايير
            criteria_scores = []
            for i in range(1, 8):
                score = request.form.get(f'criteria_{i}')
                if score:
                    criteria_scores.append(int(score))

            total_score = sum(criteria_scores) if criteria_scores else 0

            evaluation = Evaluation(
                employee_id=request.form.get('employee_id'),
                evaluator_id=current_user.id,
                evaluation_type='contractor',  # تقييم من متعهد/مالك
                score=total_score,
                comments=request.form.get('comments'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            )
            db.session.add(evaluation)
            db.session.commit()
            flash('تم إضافة تقييم المشرف بنجاح', 'success')
            return redirect(url_for('evaluations_list'))

        employees = Employee.query.filter(
            Employee.is_active == True,
            Employee.job_title.contains('مشرف')
        ).all()
        return render_template('evaluations/add_supervisor_evaluation.html',
                               employees=employees,
                               now=datetime.now())

    # ==================== تقييم المناطق والمواقع ====================

    @app.route('/evaluations/areas')
    @login_required
    def area_evaluations_list():
        """عرض تقييمات المناطق والمواقع"""
        evaluations = AreaEvaluation.query.order_by(AreaEvaluation.evaluation_date.desc()).all()

        # إحصائيات
        stats = {
            'total': len(evaluations),
            'regions': len([e for e in evaluations if e.evaluation_type == 'region']),
            'locations': len([e for e in evaluations if e.evaluation_type == 'location']),
            'avg_score': sum(e.overall_score for e in evaluations) / len(evaluations) if evaluations else 0,
            'pending': len([e for e in evaluations if e.status == 'pending']),
            'approved': len([e for e in evaluations if e.status == 'approved'])
        }

        return render_template('evaluations/area_evaluations.html',
                               evaluations=evaluations,
                               stats=stats,
                               now=datetime.now())

    @app.route('/evaluations/areas/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def add_area_evaluation():
        """إضافة تقييم جديد لمنطقة أو موقع"""
        if request.method == 'POST':
            evaluation_type = request.form.get('evaluation_type')
            region_id = request.form.get('region_id')
            location_id = request.form.get('location_id')
            comments = request.form.get('comments', '')
            status = request.form.get('status', 'pending')

            # جمع درجات المعايير
            criteria_scores = []
            total_score = 0
            max_possible = 0

            for key, value in request.form.items():
                if key.startswith('criteria_'):
                    criteria_id = int(key.split('_')[1])
                    score = int(value)

                    criteria = AreaEvaluationCriteria.query.get(criteria_id)
                    if criteria:
                        criteria_scores.append({
                            'criteria_id': criteria_id,
                            'name': criteria.name,
                            'score': score,
                            'max_score': criteria.max_score,
                            'weight': criteria.weight
                        })
                        total_score += score * criteria.weight
                        max_possible += criteria.max_score * criteria.weight

            # حساب النسبة المئوية
            overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0

            evaluation = AreaEvaluation(
                evaluation_type=evaluation_type,
                region_id=region_id if evaluation_type == 'region' else None,
                location_id=location_id if evaluation_type == 'location' else None,
                evaluation_date=datetime.strptime(request.form.get('evaluation_date'), '%Y-%m-%d').date(),
                evaluator_id=current_user.id,
                overall_score=round(overall_score, 1),
                comments=comments,
                status=status
            )
            evaluation.set_criteria_scores(criteria_scores)
            db.session.add(evaluation)
            db.session.commit()

            flash('✅ تم إضافة تقييم المنطقة/الموقع بنجاح', 'success')
            return redirect(url_for('area_evaluations_list'))

        # GET request
        regions = Region.query.all()
        locations = Location.query.all()

        # جلب معايير التقييم
        region_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='region', is_active=True
        ).order_by(AreaEvaluationCriteria.order).all()

        location_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='location', is_active=True
        ).order_by(AreaEvaluationCriteria.order).all()

        return render_template('evaluations/add_area_evaluation.html',
                               regions=regions,
                               locations=locations,
                               region_criteria=region_criteria,
                               location_criteria=location_criteria,
                               now=datetime.now())

    @app.route('/evaluations/areas/view/<int:evaluation_id>')
    @login_required
    def view_area_evaluation(evaluation_id):
        """عرض تفاصيل تقييم المنطقة/الموقع"""
        evaluation = AreaEvaluation.query.get_or_404(evaluation_id)
        return render_template('evaluations/view_area_evaluation.html',
                               evaluation=evaluation,
                               now=datetime.now())

    @app.route('/evaluations/areas/edit/<int:evaluation_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def edit_area_evaluation(evaluation_id):
        """تعديل تقييم المنطقة/الموقع"""
        evaluation = AreaEvaluation.query.get_or_404(evaluation_id)

        if request.method == 'POST':
            try:
                evaluation.comments = request.form.get('comments', '')
                evaluation.status = request.form.get('status', 'pending')

                # تحديث الدرجات
                criteria_scores = []
                total_score = 0
                max_possible = 0

                for key, value in request.form.items():
                    if key.startswith('criteria_'):
                        criteria_id = int(key.split('_')[1])
                        score = int(value)

                        criteria = AreaEvaluationCriteria.query.get(criteria_id)
                        if criteria:
                            criteria_scores.append({
                                'criteria_id': criteria_id,
                                'name': criteria.name,
                                'score': score,
                                'max_score': criteria.max_score,
                                'weight': criteria.weight
                            })
                            total_score += score * criteria.weight
                            max_possible += criteria.max_score * criteria.weight

                evaluation.overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0
                evaluation.set_criteria_scores(criteria_scores)
                db.session.commit()

                flash('✅ تم تحديث التقييم بنجاح', 'success')
                return redirect(url_for('area_evaluations_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        # GET request
        regions = Region.query.all()
        locations = Location.query.all()

        region_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='region', is_active=True
        ).order_by(AreaEvaluationCriteria.order).all()

        location_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='location', is_active=True
        ).order_by(AreaEvaluationCriteria.order).all()

        return render_template('evaluations/edit_area_evaluation.html',
                               evaluation=evaluation,
                               regions=regions,
                               locations=locations,
                               region_criteria=region_criteria,
                               location_criteria=location_criteria,
                               now=datetime.now())

    @app.route('/evaluations/areas/delete/<int:evaluation_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_area_evaluation(evaluation_id):
        """حذف تقييم المنطقة/الموقع"""
        evaluation = AreaEvaluation.query.get_or_404(evaluation_id)

        try:
            db.session.delete(evaluation)
            db.session.commit()
            flash('✅ تم حذف التقييم بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

        return redirect(url_for('area_evaluations_list'))

    @app.route('/evaluations/areas/criteria', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def manage_area_criteria():
        """إدارة معايير تقييم المناطق والمواقع"""
        if request.method == 'POST':
            evaluation_type = request.form.get('evaluation_type')
            name = request.form.get('name')
            description = request.form.get('description')
            weight = float(request.form.get('weight', 1))
            max_score = int(request.form.get('max_score', 10))
            order = int(request.form.get('order', 0))

            criteria = AreaEvaluationCriteria(
                evaluation_type=evaluation_type,
                name=name,
                description=description,
                weight=weight,
                max_score=max_score,
                order=order
            )
            db.session.add(criteria)
            db.session.commit()
            flash(f'✅ تم إضافة معيار "{name}" بنجاح', 'success')
            return redirect(url_for('manage_area_criteria'))

        # GET request
        region_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='region'
        ).order_by(AreaEvaluationCriteria.order).all()

        location_criteria = AreaEvaluationCriteria.query.filter_by(
            evaluation_type='location'
        ).order_by(AreaEvaluationCriteria.order).all()

        return render_template('evaluations/area_criteria.html',
                               region_criteria=region_criteria,
                               location_criteria=location_criteria,
                               now=datetime.now())

    @app.route('/evaluations/areas/criteria/delete/<int:criteria_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_area_criteria(criteria_id):
        """حذف معيار تقييم"""
        criteria = AreaEvaluationCriteria.query.get_or_404(criteria_id)
        criteria.is_active = False
        db.session.commit()
        flash('✅ تم حذف المعيار بنجاح', 'success')
        return redirect(url_for('manage_area_criteria'))

    @app.route('/invoices/partial_payments/<int:invoice_id>')
    @login_required
    def invoice_partial_payments(invoice_id):
        """عرض سجل المدفوعات الجزئية للفاتورة"""
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template('contracts/invoice_payments.html', invoice=invoice)

    # ==================== التقارير ====================
    @app.route('/reports/dashboard')
    @login_required
    def reports_dashboard():
        from sqlalchemy import func

        if current_user.role == 'admin':
            total_employees = Employee.query.filter_by(is_active=True).count()
            total_companies = Company.query.count()
            today_attendance = Attendance.query.filter_by(date=datetime.now().date(),
                                                          attendance_status='present').count()
        elif current_user.role == 'supervisor':
            # المشرف يرى فقط عمال شركته
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                total_employees = Employee.query.filter_by(is_active=True,
                                                           company_id=supervisor_employee.company_id).count()
                total_companies = 1
                # جلب عمال الشركة للحضور
                workers = Employee.query.filter_by(company_id=supervisor_employee.company_id, is_active=True).all()
                worker_ids = [w.id for w in workers]
                today_attendance = Attendance.query.filter(
                    Attendance.date == datetime.now().date(),
                    Attendance.attendance_status == 'present',
                    Attendance.employee_id.in_(worker_ids)
                ).count()
            else:
                total_employees = 0
                total_companies = 0
                today_attendance = 0
        else:
            total_employees = 0
            total_companies = 0
            today_attendance = 0

        current_month = datetime.now().strftime('%m-%Y')
        total_salaries_month = db.session.query(func.sum(Salary.total_salary)).filter_by(
            month_year=current_month).scalar() or 0

        attendance_rate = round((today_attendance / total_employees * 100) if total_employees > 0 else 0)

        return render_template('reports/dashboard.html',
                               total_employees=total_employees,
                               total_companies=total_companies,
                               total_salaries_month=total_salaries_month,
                               attendance_rate=attendance_rate)

    @app.route('/reports/attendance')
    @login_required
    def attendance_report():
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id', type=int)

        query = Attendance.query
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)

        attendances = query.all()
        employees = Employee.query.filter_by(is_active=True).all()

        return render_template('reports/attendance_report.html',
                               attendances=attendances,
                               employees=employees,
                               now=datetime.now())

    # ==================== تعديل وحذف سجلات الحضور من التقرير ====================

    @app.route('/attendance/edit/<int:attendance_id>', methods=['GET', 'POST'])
    @login_required
    def edit_attendance_record(attendance_id):
        """تعديل سجل حضور محدد"""
        attendance = Attendance.query.get_or_404(attendance_id)

        # حفظ معلمات الفلترة للعودة إليها
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        employee_id = request.args.get('employee_id', '')

        if request.method == 'POST':
            try:
                # تحديث البيانات من النموذج
                attendance.attendance_status = request.form.get('attendance_status')
                attendance.attendance_type = request.form.get('attendance_type')
                attendance.late_minutes = int(request.form.get('late_minutes', 0))

                # معالجة وقت الدخول
                if request.form.get('check_in_time'):
                    attendance.check_in_time = datetime.strptime(request.form.get('check_in_time'), '%H:%M').time()
                else:
                    attendance.check_in_time = None

                # معالجة وقت الخروج
                if request.form.get('check_out_time'):
                    attendance.check_out_time = datetime.strptime(request.form.get('check_out_time'), '%H:%M').time()
                else:
                    attendance.check_out_time = None

                # تحديث الملاحظات
                attendance.notes = request.form.get('notes', '')

                # تحديث حالة الإجازة المرضية
                attendance.sick_leave = attendance.attendance_status == 'sick'
                if attendance.attendance_status == 'sick':
                    attendance.sick_leave_days = int(request.form.get('sick_leave_days', 1))
                else:
                    attendance.sick_leave_days = 0

                db.session.commit()
                flash('✅ تم تحديث سجل الحضور بنجاح', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

            # العودة إلى تقرير الحضور مع الحفاظ على الفلاتر
            return redirect(url_for('attendance_report',
                                    start_date=request.form.get('start_date'),
                                    end_date=request.form.get('end_date'),
                                    employee_id=request.form.get('employee_id')))

        # GET request - عرض نموذج التعديل
        return render_template('attendance/edit_attendance.html',
                               attendance=attendance,
                               start_date=start_date,
                               end_date=end_date,
                               employee_id=employee_id)

    @app.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
    @login_required
    def delete_attendance_record(attendance_id):
        """حذف سجل حضور محدد"""
        attendance = Attendance.query.get_or_404(attendance_id)

        # حفظ معلمات الفلترة للعودة إليها
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        employee_id = request.form.get('employee_id', '')

        try:
            db.session.delete(attendance)
            db.session.commit()
            flash('✅ تم حذف سجل الحضور بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

        # العودة إلى تقرير الحضور مع الحفاظ على الفلاتر
        return redirect(url_for('attendance_report',
                                start_date=start_date,
                                end_date=end_date,
                                employee_id=employee_id))

    @app.route('/reports/financial')
    @login_required
    @role_required('admin', 'finance')
    def financial_report():
        """تقرير الرواتب - يعرض تفاصيل رواتب الموظفين"""

        month_year = request.args.get('month_year', 'all')

        # الحصول على قائمة الأشهر المتاحة من الرواتب
        all_salaries_list = Salary.query.all()
        available_months = list(set([s.month_year for s in all_salaries_list]))
        available_months.sort(reverse=True)

        # إضافة خيار 'all' إذا لم يكن موجوداً
        if 'all' not in available_months:
            available_months.insert(0, 'all')

        report = None

        # عرض جميع الرواتب
        if month_year == 'all' or not month_year:
            salaries = Salary.query.order_by(Salary.month_year.desc()).all()

            if salaries:
                # تجهيز بيانات الرواتب للعرض
                salaries_data = []
                for salary in salaries:
                    # تنسيق عرض الفترة
                    period_display = salary.notes if salary.notes else salary.month_year
                    if salary.notes and 'فترة من' in salary.notes:
                        period_display = salary.notes
                    elif '_' in salary.month_year:
                        parts = salary.month_year.split('_')
                        if len(parts) == 2:
                            try:
                                start = datetime.strptime(parts[0], '%Y%m%d').date()
                                end = datetime.strptime(parts[1], '%Y%m%d').date()
                                period_display = f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"
                            except:
                                pass

                    salaries_data.append({
                        'employee': salary.employee,
                        'period_display': period_display,
                        'month_year': salary.month_year,
                        'attendance_days': salary.attendance_days,
                        'attendance_amount': salary.attendance_amount,
                        'daily_allowance_amount': salary.daily_allowance_amount,
                        'overtime_amount': salary.overtime_amount,
                        'advance_amount': salary.advance_amount,
                        'deduction_amount': salary.deduction_amount,
                        'penalty_amount': salary.penalty_amount,
                        'total_salary': salary.total_salary,
                        'is_paid': salary.is_paid
                    })

                report = {
                    'month_year': 'جميع الأشهر',
                    'start_date': None,
                    'end_date': None,
                    'total_employees': len(salaries),
                    'total_attendance_days': sum(s.attendance_days for s in salaries),
                    'total_salaries': sum(s.total_salary for s in salaries),
                    'paid_salaries': sum(1 for s in salaries if s.is_paid),
                    'salaries': salaries_data
                }

        # عرض شهر محدد
        elif month_year and month_year != 'all':
            try:
                # محاولة العثور على الرواتب بالتنسيقين
                salaries = Salary.query.filter_by(month_year=month_year).all()

                if not salaries:
                    # تجربة التنسيق الآخر
                    if '-' in month_year:
                        parts = month_year.split('-')
                        if len(parts[0]) == 4:  # YYYY-MM
                            alt_format = f"{parts[1]}-{parts[0]}"
                        else:  # MM-YYYY
                            alt_format = f"{parts[1]}-{parts[0]}"
                        salaries = Salary.query.filter_by(month_year=alt_format).all()

                if salaries:
                    start_date, end_date = get_financial_month_dates(month_year)

                    salaries_data = []
                    for salary in salaries:
                        period_display = salary.notes if salary.notes else f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

                        salaries_data.append({
                            'employee': salary.employee,
                            'period_display': period_display,
                            'month_year': salary.month_year,
                            'attendance_days': salary.attendance_days,
                            'attendance_amount': salary.attendance_amount,
                            'daily_allowance_amount': salary.daily_allowance_amount,
                            'overtime_amount': salary.overtime_amount,
                            'advance_amount': salary.advance_amount,
                            'deduction_amount': salary.deduction_amount,
                            'penalty_amount': salary.penalty_amount,
                            'total_salary': salary.total_salary,
                            'is_paid': salary.is_paid
                        })

                    report = {
                        'month_year': month_year,
                        'start_date': start_date,
                        'end_date': end_date,
                        'total_employees': len(salaries),
                        'total_attendance_days': sum(s.attendance_days for s in salaries),
                        'total_salaries': sum(s.total_salary for s in salaries),
                        'paid_salaries': sum(1 for s in salaries if s.is_paid),
                        'salaries': salaries_data
                    }
            except Exception as e:
                flash(f'خطأ في معالجة الشهر: {str(e)}', 'danger')

        return render_template('reports/financial_report.html',
                               report=report,
                               available_months=available_months,
                               selected_month=month_year,
                               now=datetime.now())

    @app.route('/reports/employees')
    @login_required
    def employees_report():
        employees = Employee.query.all()
        return render_template('reports/employees_report.html', employees=employees)

    @app.route('/reports/regions')
    @login_required
    def regions_report():
        """تقرير المناطق - عرض توزيع الموظفين حسب المناطق"""
        from sqlalchemy import func

        # جلب المناطق من الموظفين (وليس من الشركات)
        regions_result = db.session.query(
            Employee.region,
            db.func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.region != None,
            Employee.region != ''
        ).group_by(Employee.region).all()

        # تحويل إلى قائمة قواميس
        regions_data = []
        total_employees = 0

        for row in regions_result:
            region_name = row[0]
            employees_count = row[1]

            total_employees += employees_count

            # حساب عدد الشركات في هذه المنطقة (من الموظفين)
            companies_count = db.session.query(Employee.company_id).filter(
                Employee.region == region_name,
                Employee.is_active == True
            ).distinct().count()

            regions_data.append({
                'region': region_name,
                'companies_count': companies_count,
                'employees_count': employees_count
            })

        # ترتيب حسب عدد الموظفين (تنازلي)
        regions_data.sort(key=lambda x: x['employees_count'], reverse=True)

        return render_template('reports/regions_report.html',
                               regions_data=regions_data,
                               total_employees=total_employees,
                               now=datetime.now())

    @app.route('/reports/monthly_close', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def monthly_close():
        if request.method == 'POST':
            month_year = request.form.get('month_year')
            start_date, end_date = get_financial_month_dates(month_year)
            salaries = Salary.query.filter_by(month_year=month_year).all()

            report = {
                'month_year': month_year,
                'start_date': start_date,
                'end_date': end_date,
                'total_employees': len(salaries),
                'total_salaries': sum(s.total_salary for s in salaries),
                'paid_salaries': sum(1 for s in salaries if s.is_paid),
                'salaries': salaries
            }
            return render_template('reports/monthly_close_report.html', report=report)

        return render_template('reports/monthly_close.html')

    @app.route('/reports/financial_monthly')
    @login_required
    @role_required('admin', 'finance')
    def financial_monthly_report():
        """التقرير المالي الشهري"""

        year = request.args.get('year', datetime.now().year, type=int)
        month = request.args.get('month', datetime.now().month, type=int)

        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

        month_name = start_date.strftime('%B %Y')
        # ==================== الرواتب (حل مرن) ====================
        month_year_formats = [
            start_date.strftime('%Y-%m'),  # 2026-04
            start_date.strftime('%m-%Y')  # 04-2026
        ]

        salaries_total = 0
        salaries_paid = 0
        salaries_unpaid = 0

        for fmt in month_year_formats:
            salaries_paid = db.session.query(func.sum(Salary.total_salary)).filter(
                Salary.month_year == fmt,
                Salary.is_paid == True
            ).scalar() or 0

            salaries_unpaid = db.session.query(func.sum(Salary.total_salary)).filter(
                Salary.month_year == fmt,
                Salary.is_paid == False
            ).scalar() or 0

            salaries_total = salaries_paid + salaries_unpaid

            if salaries_total > 0:
                break

        print(
            f"✅ Found salaries for {start_date.strftime('%Y-%m')}: Total={salaries_total}, Paid={salaries_paid}, Unpaid={salaries_unpaid}")

        # ==================== العقود (دخل أساسي) ====================
        contracts = Contract.query.filter(
            Contract.start_date <= end_date,
            (Contract.end_date >= start_date) | (Contract.end_date.is_(None))
        ).all()

        contracts_total = 0
        contracts_details = []

        for contract in contracts:
            if contract.contract_type == 'monthly':
                monthly_value = contract.contract_value
            else:
                monthly_value = contract.contract_value / 12

            contracts_total += monthly_value

            contracts_details.append({
                'company_name': contract.company.name if contract.company else '-',
                'contract_type': contract.contract_type,
                'total_value': contract.contract_value,
                'monthly_value': monthly_value
            })

        # ==================== الفواتير ====================

        # فواتير مدفوعة (دخل إضافي فعلي)
        invoices_paid = Invoice.query.filter(
            Invoice.paid_date >= start_date,
            Invoice.paid_date <= end_date,
            Invoice.is_paid == True
        ).all()

        invoices_paid_total = sum(i.amount for i in invoices_paid)

        # فواتير مستحقة (للعرض فقط)
        invoices_due = Invoice.query.filter(
            Invoice.due_date >= start_date,
            Invoice.due_date <= end_date,
            Invoice.is_paid == False
        ).all()

        invoices_due_total = sum(i.amount for i in invoices_due)

        # ==================== المصروفات ====================
        # ==================== المصروفات ====================
        # استخدام FinancialTransaction بدلاً من Expense (لأن Expense غير موجود)
        expenses = FinancialTransaction.query.filter(
            FinancialTransaction.transaction_type.in_(['deduction', 'penalty']),
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        ).all()
        expenses_total = sum(e.amount for e in expenses) if expenses else 0

        # السلف
        advances = FinancialTransaction.query.filter(
            FinancialTransaction.transaction_type == 'advance',
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        ).all()
        advances_total = sum(a.amount for a in advances)
        # ==================== الإضافات (للعرض فقط) ====================
        overtime = FinancialTransaction.query.filter(
            FinancialTransaction.transaction_type == 'overtime',
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        ).all()
        overtime_total = sum(o.amount for o in overtime)
        # ==================== الحسابات النهائية ====================

        # 🔴 المصروفات
        total_expenses = salaries_total + expenses_total + advances_total

        # 🟢 الإيرادات (العقود + الفواتير)
        total_income = contracts_total + invoices_paid_total

        # الربح
        profit = total_income - total_expenses

        # ==================== بيانات الشركات ====================
        # ==================== بيانات الشركات (معدلة) ====================
        companies_data = []
        for company in Company.query.all():
            # دخل العقود
            company_contracts = Contract.query.filter_by(company_id=company.id).all()
            company_contracts_value = 0
            for c in company_contracts:
                if c.contract_type == 'monthly':
                    company_contracts_value += c.contract_value
                else:
                    company_contracts_value += c.contract_value / 12

            # ✅ الفواتير المدفوعة لهذه الشركة (خارج العقود)
            company_invoices = db.session.query(func.sum(Invoice.amount)).filter(
                Invoice.paid_date >= start_date,
                Invoice.paid_date <= end_date,
                Invoice.is_paid == True
            ).join(Contract).filter(Contract.company_id == company.id).scalar() or 0

            # ✅ إجمالي الإيرادات = العقود + الفواتير
            company_total_income = company_contracts_value + company_invoices

            # رواتب الشركة
            company_salaries = 0

            for fmt in month_year_formats:
                value = db.session.query(func.sum(Salary.total_salary)).filter(
                    Salary.month_year == fmt,
                    Salary.is_paid == True
                ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

                if value > 0:
                    company_salaries = value
                    break

            # سلف الشركة
            company_advances = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.transaction_type == 'advance',
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

            # إضافيات الشركة
            company_overtime = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.transaction_type == 'overtime',
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

            # ✅ إجمالي المصروفات = الرواتب + السلف + الإضافات
            company_total_expenses = company_salaries + (company_advances or 0) + (company_overtime or 0)

            # صافي الربح
            company_net = company_total_income - company_total_expenses

            companies_data.append({
                'name': company.name,
                'contracts_value': company_contracts_value,
                'invoices_value': company_invoices,
                'total_income': company_total_income,  # ✅ جديد
                'salaries': company_salaries,
                'advances': company_advances or 0,
                'overtime': company_overtime or 0,
                'total_expenses': company_total_expenses,  # ✅ جديد
                'net': company_net
            })
        # ==================== الأشهر ====================
        available_months = []
        for y in range(2023, datetime.now().year + 1):
            for m in range(1, 13):
                if datetime(y, m, 1) <= datetime.now():
                    available_months.append({
                        'year': y,
                        'month': m,
                        'name': f'{y}-{str(m).zfill(2)}'
                    })

        return render_template('reports/financial_monthly.html',
                               month_name=month_name,
                               year=year,
                               month=month,
                               salaries_total=salaries_total,
                               salaries_paid=salaries_paid,
                               salaries_unpaid=salaries_unpaid,
                               contracts_total=contracts_total,
                               contracts_details=contracts_details,
                               invoices_due_total=invoices_due_total,
                               invoices_due=invoices_due,
                               invoices_paid_total=invoices_paid_total,
                               expenses_total=expenses_total,
                               expenses=expenses,
                               advances_total=advances_total,
                               overtime_total=overtime_total,
                               total_expenses=total_expenses,
                               total_income=total_income,
                               profit=profit,
                               companies_data=companies_data,
                               available_months=available_months,
                               now=datetime.now())

    @app.route('/reports/evaluations_analysis')
    @login_required
    def evaluations_analysis_report():
        """تقرير تحليل التقييمات"""
        # فلترة حسب الفترة
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        company_id = request.args.get('company_id', type=int)
        region_id = request.args.get('region_id', type=int)
        location_id = request.args.get('location_id', type=int)

        query = Evaluation.query

        if start_date:
            query = query.filter(Evaluation.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Evaluation.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if company_id:
            query = query.join(Employee).filter(Employee.company_id == company_id)
        if region_id:
            query = query.join(Employee).filter(Employee.region == region_id)

        evaluations = query.all()

        # إحصائيات التقييمات
        total_evaluations = len(evaluations)
        avg_score = sum(e.score for e in evaluations) / total_evaluations if total_evaluations > 0 else 0

        # توزيع التقييمات
        excellent = len([e for e in evaluations if e.score >= 90])
        very_good = len([e for e in evaluations if 75 <= e.score < 90])
        good = len([e for e in evaluations if 60 <= e.score < 75])
        fair = len([e for e in evaluations if 50 <= e.score < 60])
        poor = len([e for e in evaluations if e.score < 50])

        # أفضل الموظفين
        employee_scores = {}
        for e in evaluations:
            if e.employee_id not in employee_scores:
                employee_scores[e.employee_id] = {'total': 0, 'count': 0, 'name': e.employee.name}
            employee_scores[e.employee_id]['total'] += e.score
            employee_scores[e.employee_id]['count'] += 1

        top_employees = []
        for emp_id, data in employee_scores.items():
            avg = data['total'] / data['count']
            top_employees.append({
                'name': data['name'],
                'avg_score': avg,
                'count': data['count']
            })
        top_employees.sort(key=lambda x: x['avg_score'], reverse=True)

        # التقييم حسب المعايير (للمعايير الديناميكية)
        criteria_scores = {}
        for e in evaluations:
            # هذا يحتاج إلى تخزين تفاصيل المعايير في جدول منفصل
            pass

        # البيانات للفلترة
        companies = Company.query.all()
        regions = get_regions()
        locations = Location.query.all()

        return render_template('reports/evaluations_analysis.html',
                               total_evaluations=total_evaluations,
                               avg_score=avg_score,
                               excellent=excellent,
                               very_good=very_good,
                               good=good,
                               fair=fair,
                               poor=poor,
                               top_employees=top_employees[:10],
                               companies=companies,
                               regions=regions,
                               locations=locations,
                               start_date=start_date,
                               end_date=end_date,
                               selected_company=company_id,
                               selected_region=region_id,
                               selected_location=location_id,
                               now=datetime.now())

    @app.route('/reports/evaluations_by_location')
    @login_required
    def evaluations_by_location_report():
        """تقرير تقييمات العمال حسب الموقع"""
        location_id = request.args.get('location_id', type=int)

        # جلب جميع التقييمات من نوع المشرف
        query = Evaluation.query.filter(Evaluation.evaluation_type == 'supervisor')

        if location_id:
            query = query.filter(Evaluation.location_id == location_id)

        evaluations = query.order_by(Evaluation.date.desc()).all()

        # جلب جميع المواقع
        locations = Location.query.all()

        # إنشاء قاموس للمواقع مع إحصائياتها
        location_stats = []
        for location in locations:
            # جلب التقييمات الخاصة بهذا الموقع
            location_evaluations = [e for e in evaluations if e.location_id == location.id]
            if location_evaluations:
                avg_score = sum(e.score for e in location_evaluations) / len(location_evaluations)
                location_stats.append({
                    'location_id': location.id,
                    'location_name': location.name,
                    'region_name': location.region.name if location.region else '-',
                    'count': len(location_evaluations),
                    'avg_score': round(avg_score, 1),
                    'evaluations': location_evaluations
                })

        # ترتيب المواقع حسب عدد التقييمات
        location_stats.sort(key=lambda x: x['count'], reverse=True)

        return render_template('reports/evaluations_by_location.html',
                               evaluations=evaluations,
                               locations=locations,
                               location_stats=location_stats,
                               selected_location=location_id,
                               now=datetime.now())

    @app.route('/reports/evaluations_by_region')
    @login_required
    def evaluations_by_region_report():
        """تقرير تقييمات العمال حسب المنطقة"""
        region_id = request.args.get('region_id', type=int)

        # جلب جميع التقييمات من نوع المشرف
        query = Evaluation.query.filter(Evaluation.evaluation_type == 'supervisor')

        if region_id:
            query = query.filter(Evaluation.region_id == region_id)

        evaluations = query.order_by(Evaluation.date.desc()).all()

        # جلب جميع المناطق
        regions = Region.query.all()

        # إنشاء قاموس للمناطق مع إحصائياتها
        region_stats = []
        for region in regions:
            # جلب التقييمات الخاصة بهذه المنطقة
            region_evaluations = [e for e in evaluations if e.region_id == region.id]
            if region_evaluations:
                avg_score = sum(e.score for e in region_evaluations) / len(region_evaluations)
                region_stats.append({
                    'region_id': region.id,
                    'region_name': region.name,
                    'company_name': region.company.name if region.company else '-',
                    'count': len(region_evaluations),
                    'avg_score': round(avg_score, 1),
                    'evaluations': region_evaluations  # ✅ حفظ التقييمات مباشرة
                })

        # ترتيب المناطق حسب عدد التقييمات
        region_stats.sort(key=lambda x: x['count'], reverse=True)

        return render_template('reports/evaluations_by_region.html',
                               evaluations=evaluations,
                               regions=regions,
                               region_stats=region_stats,
                               selected_region=region_id,
                               now=datetime.now())

    @app.route('/api/evaluation/<int:evaluation_id>')
    @login_required
    def get_evaluation_details(evaluation_id):
        """API لجلب تفاصيل التقييم للـ Modal"""
        evaluation = Evaluation.query.get_or_404(evaluation_id)

        return jsonify({
            'success': True,
            'id': evaluation.id,
            'employee_name': evaluation.employee.name,
            'job_title': evaluation.employee.job_title,
            'region_name': evaluation.region.name if evaluation.region else None,
            'location_name': evaluation.location.name if evaluation.location else None,
            'date': evaluation.date.strftime('%Y-%m-%d'),
            'score': evaluation.score,
            'comments': evaluation.comments,
            'criteria_scores': evaluation.get_criteria_scores()
        })

    # ==================== تصدير التقارير إلى PDF ====================

    from flask import make_response
    from weasyprint import HTML
    import tempfile
    import os

    @app.route('/reports/evaluations_by_region/pdf')
    @login_required
    def export_evaluations_by_region_pdf():
        """تصدير تقرير التقييمات حسب المنطقة إلى PDF"""

        # جلب نفس البيانات المستخدمة في التقرير
        evaluations = Evaluation.query.filter(
            Evaluation.evaluation_type == 'supervisor'
        ).order_by(Evaluation.date.desc()).all()

        regions = Region.query.all()

        region_stats = []
        for region in regions:
            region_evaluations = [e for e in evaluations if e.region_id == region.id]
            if region_evaluations:
                avg_score = sum(e.score for e in region_evaluations) / len(region_evaluations)
                region_stats.append({
                    'region_id': region.id,
                    'region_name': region.name,
                    'company_name': region.company.name if region.company else '-',
                    'count': len(region_evaluations),
                    'avg_score': round(avg_score, 1),
                    'evaluations': region_evaluations
                })

        # ترتيب المناطق حسب عدد التقييمات
        region_stats.sort(key=lambda x: x['count'], reverse=True)

        # إحصائيات عامة
        total_evaluations = len(evaluations)
        total_employees = len(set([e.employee_id for e in evaluations]))
        overall_avg = sum(e.score for e in evaluations) / total_evaluations if total_evaluations > 0 else 0

        # إنشاء HTML للـ PDF
        html_content = render_template('reports/pdf/evaluations_by_region_pdf.html',
                                       region_stats=region_stats,
                                       total_evaluations=total_evaluations,
                                       total_employees=total_employees,
                                       overall_avg=round(overall_avg, 1),
                                       now=datetime.now(),
                                       current_user=current_user)

        # تحويل HTML إلى PDF
        pdf = HTML(string=html_content).write_pdf()

        # إنشاء استجابة PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers[
            'Content-Disposition'] = f'attachment; filename=evaluations_by_region_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return response

    @app.route('/reports/evaluations_by_location/pdf')
    @login_required
    def export_evaluations_by_location_pdf():
        """تصدير تقرير التقييمات حسب الموقع إلى PDF"""

        evaluations = Evaluation.query.filter(
            Evaluation.evaluation_type == 'supervisor'
        ).order_by(Evaluation.date.desc()).all()

        locations = Location.query.all()

        location_stats = []
        for location in locations:
            location_evaluations = [e for e in evaluations if e.location_id == location.id]
            if location_evaluations:
                avg_score = sum(e.score for e in location_evaluations) / len(location_evaluations)
                location_stats.append({
                    'location_id': location.id,
                    'location_name': location.name,
                    'region_name': location.region.name if location.region else '-',
                    'count': len(location_evaluations),
                    'avg_score': round(avg_score, 1),
                    'evaluations': location_evaluations
                })

        location_stats.sort(key=lambda x: x['count'], reverse=True)

        total_evaluations = len(evaluations)
        total_employees = len(set([e.employee_id for e in evaluations]))
        overall_avg = sum(e.score for e in evaluations) / total_evaluations if total_evaluations > 0 else 0

        html_content = render_template('reports/pdf/evaluations_by_location_pdf.html',
                                       location_stats=location_stats,
                                       total_evaluations=total_evaluations,
                                       total_employees=total_employees,
                                       overall_avg=round(overall_avg, 1),
                                       now=datetime.now(),
                                       current_user=current_user)

        pdf = HTML(string=html_content).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers[
            'Content-Disposition'] = f'attachment; filename=evaluations_by_location_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return response

    @app.route('/reports/attendance/pdf')
    @login_required
    def export_attendance_pdf():
        """تصدير تقرير الحضور إلى PDF"""

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id', type=int)

        query = Attendance.query
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)

        attendances = query.order_by(Attendance.date.desc()).all()
        employees = Employee.query.filter_by(is_active=True).all()

        html_content = render_template('reports/pdf/attendance_pdf.html',
                                       attendances=attendances,
                                       employees=employees,
                                       start_date=start_date,
                                       end_date=end_date,
                                       now=datetime.now(),
                                       current_user=current_user)

        pdf = HTML(string=html_content).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers[
            'Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return response

    @app.route('/reports/financial/pdf')
    @login_required
    def export_financial_pdf():
        """تصدير التقرير المالي إلى PDF"""

        month_year = request.args.get('month_year')

        if month_year and month_year != 'all':
            salaries = Salary.query.filter_by(month_year=month_year).all()
            start_date, end_date = get_financial_month_dates(month_year)
            report_title = f'تقرير الرواتب - {month_year}'
        else:
            salaries = Salary.query.order_by(Salary.month_year.desc()).all()
            start_date = None
            end_date = None
            report_title = 'تقرير الرواتب - جميع الأشهر'

        total_salaries = sum(s.total_salary for s in salaries)
        total_attendance_days = sum(s.attendance_days for s in salaries)
        paid_salaries = sum(1 for s in salaries if s.is_paid)

        html_content = render_template('reports/pdf/financial_pdf.html',
                                       salaries=salaries,
                                       total_salaries=total_salaries,
                                       total_attendance_days=total_attendance_days,
                                       paid_salaries=paid_salaries,
                                       report_title=report_title,
                                       start_date=start_date,
                                       end_date=end_date,
                                       now=datetime.now(),
                                       current_user=current_user)

        pdf = HTML(string=html_content).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers[
            'Content-Disposition'] = f'attachment; filename=financial_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        return response

    # ==================== نظام الحسابات ====================

    # ==================== الرواتب (مع صلاحيات) ====================
    @app.route('/financial/salaries')
    @login_required
    @role_required('admin', 'finance', 'supervisor')
    def salaries_list():
        """عرض الرواتب - حسب صلاحية المستخدم مع فلترة متقدمة"""

        # الحصول على معاملات الفلترة
        period_key = request.args.get('period_key', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        status_filter = request.args.get('status', 'all')  # all, paid, unpaid
        employee_id = request.args.get('employee_id', type=int)

        query = Salary.query

        # فلترة حسب الفترة (مفتاح الفترة)
        if period_key:
            query = query.filter(Salary.month_year == period_key)

        # فلترة حسب التاريخ (للتوافق مع الإصدارات القديمة)
        if start_date and end_date and not period_key:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                # البحث عن الفترات التي تتضمن هذه التواريخ
                query = query.filter(
                    Salary.month_year.contains(str(start.year)) |
                    Salary.month_year.contains(str(end.year))
                )
            except:
                pass

        # فلترة حسب الحالة (مدفوع/غير مدفوع)
        if status_filter == 'paid':
            query = query.filter(Salary.is_paid == True)
        elif status_filter == 'unpaid':
            query = query.filter(Salary.is_paid == False)

        # فلترة حسب الموظف
        if employee_id:
            query = query.filter(Salary.employee_id == employee_id)

        # تطبيق صلاحية المشرف
        if current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                worker_ids = [e.id for e in
                              Employee.query.filter_by(supervisor_id=supervisor_employee.id, is_active=True).all()]
                query = query.filter(Salary.employee_id.in_(worker_ids))
            else:
                query = query.filter(False)

        all_salaries = query.order_by(Salary.month_year.desc()).all()

        # الحصول على قائمة الفترات المتاحة للفلترة
        available_periods = []
        all_salaries_for_periods = Salary.query.order_by(Salary.month_year.desc()).all()
        seen = set()
        for salary in all_salaries_for_periods:
            if salary.month_year not in seen:
                seen.add(salary.month_year)
                if salary.notes and 'فترة من' in salary.notes:
                    display = salary.notes
                else:
                    # محاولة استخراج التواريخ من المفتاح
                    if '_' in salary.month_year:
                        parts = salary.month_year.split('_')
                        if len(parts) == 2:
                            try:
                                start = datetime.strptime(parts[0], '%Y%m%d').date()
                                end = datetime.strptime(parts[1], '%Y%m%d').date()
                                display = f"فترة من {start.strftime('%d/%m/%Y')} إلى {end.strftime('%d/%m/%Y')}"
                            except:
                                display = salary.month_year
                        else:
                            display = salary.month_year
                    else:
                        display = salary.month_year
                available_periods.append({
                    'key': salary.month_year,
                    'display': display
                })

        # إحصائيات سريعة
        stats = {
            'total': len(all_salaries),
            'paid': sum(1 for s in all_salaries if s.is_paid),
            'unpaid': sum(1 for s in all_salaries if not s.is_paid),
            'total_amount': sum(s.total_salary for s in all_salaries),
            'paid_amount': sum(s.total_salary for s in all_salaries if s.is_paid),
            'unpaid_amount': sum(s.total_salary for s in all_salaries if not s.is_paid),
            'zero_or_negative': sum(1 for s in all_salaries if s.total_salary <= 0)
        }

        # الموظفين للفلترة
        employees = Employee.query.filter_by(is_active=True).all()

        return render_template('financial/salaries.html',
                               salaries=all_salaries,
                               available_periods=available_periods,
                               stats=stats,
                               employees=employees,
                               selected_period=period_key,
                               selected_status=status_filter,
                               selected_employee=employee_id,
                               start_date=start_date,
                               end_date=end_date,
                               now=datetime.now())

    @app.route('/financial/salary_calculation', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def salary_calculation():
        """حساب الرواتب - يجب أن يتم عبر ترحيل الفترات أولاً"""

        if request.method == 'POST':
            transfer_id = request.form.get('transfer_id')
            if not transfer_id:
                flash('⚠️ الرجاء اختيار فترة ترحيل أولاً', 'danger')
                return redirect(url_for('salary_calculation'))

            transfer = AttendancePeriodTransfer.query.get(transfer_id)
            if not transfer:
                flash('⚠️ فترة الترحيل غير موجودة', 'danger')
                return redirect(url_for('salary_calculation'))
            if transfer.is_transferred:
                flash(f'⚠️ فترة الترحيل "{transfer.period_name}" تم ترحيلها مسبقاً', 'warning')
                return redirect(url_for('salary_calculation'))
            if not transfer.transfers_details:
                flash('⚠️ لا توجد بيانات في فترة الترحيل المحددة', 'danger')
                return redirect(url_for('salary_calculation'))

            try:
                start_date = transfer.start_date
                end_date = transfer.end_date
                period_name = transfer.period_name
                count = 0
                total_salaries = 0

                for detail in transfer.transfers_details:
                    employee = detail.employee
                    if not employee:
                        continue

                    period_key = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

                    # البحث عن راتب موجود أو إنشاء جديد
                    salary = Salary.query.filter_by(
                        employee_id=employee.id,
                        month_year=period_key
                    ).first()

                    if not salary:
                        salary = Salary(
                            employee_id=employee.id,
                            month_year=period_key,
                            base_salary=employee.salary,
                            notes=f"فترة من {start_date} إلى {end_date}"
                        )
                        db.session.add(salary)

                    # استخدام الدالة الموجودة في نموذج Salary لحساب الراتب
                    # هذه الدالة ستستدعي employee.calculate_salary_breakdown تلقائياً
                    salary.calculate_from_preparation_detail(detail)

                    # جلب المعاملات المالية
                    advances = employee.get_transactions_sum('advance', start_date, end_date)
                    deductions = employee.get_transactions_sum('deduction', start_date, end_date)
                    penalties = employee.get_transactions_sum('penalty', start_date, end_date)

                    # تطبيق الخصومات على الراتب النهائي
                    final_salary = salary.total_salary - advances - deductions - penalties
                    salary.total_salary = final_salary
                    salary.advance_amount = advances
                    salary.deduction_amount = deductions
                    salary.penalty_amount = penalties

                    total_salaries += final_salary

                    # طباعة تفاصيل الراتب للتصحيح
                    if employee.employee_type == 'worker':
                        print(f"\n{'=' * 50}")
                        print(f"📊 راتب {employee.name}:")
                        print(f"{'=' * 50}")
                        print(f"   أيام الحضور: {detail.attendance_days}")
                        print(f"   يصرف للعامل: {salary.total_salary:,.0f} ريال")
                        print(f"   الراتب الأساسي: {salary.basic_salary_amount:,.0f} ريال")
                        print(f"   بدل السكن: {salary.resident_allowance_amount:,.0f} ريال")
                        print(f"   بدل الملابس: {salary.clothing_allowance_amount:,.0f} ريال")
                        print(f"   بطاقة صحية: {salary.health_card_amount:,.0f} ريال")
                        print(f"   تأمين: {salary.insurance_amount:,.0f} ريال")
                        print(f"   ربح المتعهد: {salary.contractor_profit:,.0f} ريال")
                        print(f"{'=' * 50}\n")
                    else:
                        print(f"\n📊 راتب {employee.name} (مشرف): {salary.total_salary:,.0f} ريال")

                    # ترحيل المعاملات المالية
                    for trans in employee.transactions:
                        if not trans.is_settled and start_date <= trans.date <= end_date:
                            trans.is_settled = True
                            trans.settled_date = end_date

                    detail.is_processed = True
                    count += 1

                transfer.is_transferred = True
                transfer.transfer_date = datetime.now().date()
                db.session.commit()

                flash(f'✅ تم حساب وترحيل رواتب {count} موظف من فترة "{period_name}"', 'success')
                flash(f'💰 إجمالي الرواتب: {total_salaries:,.0f} ريال', 'info')
                return redirect(url_for('salaries_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')
                print(f"❌ خطأ: {e}")
                import traceback
                traceback.print_exc()
                return redirect(url_for('salary_calculation'))

        # GET request
        pending_transfers = AttendancePeriodTransfer.query.filter_by(is_transferred=False).order_by(
            AttendancePeriodTransfer.start_date.desc()).all()
        completed_transfers = AttendancePeriodTransfer.query.filter_by(is_transferred=True).order_by(
            AttendancePeriodTransfer.start_date.desc()).limit(10).all()
        return render_template('financial/salary_calculation.html',
                               pending_transfers=pending_transfers,
                               completed_transfers=completed_transfers)

    @app.route('/financial/salaries/pay/<int:salary_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def pay_salary(salary_id):
        """صرف راتب - مع إنشاء استحقاق تلقائي إذا لم يكن موجوداً"""
        from models import Account, JournalEntry, JournalEntryDetail
        from datetime import datetime
        from utils import get_next_entry_number, create_salary_journal_entry

        salary = Salary.query.get_or_404(salary_id)

        # ========== 1. التحقق من وجود قيد استحقاق ==========
        accrual_entry = JournalEntry.query.filter(
            JournalEntry.reference_type == 'salary',  # ✅ تغيير من salary_accrual إلى salary
            JournalEntry.reference_id == salary.id
        ).first()

        # ✅ إذا لم يكن هناك استحقاق، قم بإنشائه تلقائياً
        if not accrual_entry:
            flash('⚠️ لا يوجد قيد استحقاق للراتب. جاري إنشاؤه تلقائياً...', 'info')
            try:
                accrual_entry = create_salary_journal_entry(salary)
                flash(f'✅ تم إنشاء قيد استحقاق الراتب: {accrual_entry.entry_number}', 'success')
            except Exception as e:
                flash(f'❌ حدث خطأ في إنشاء استحقاق الراتب: {str(e)}', 'danger')
                return redirect(url_for('salaries_list'))

        # ========== 2. عرض نموذج الصرف (GET) ==========
        if request.method == 'GET':
            cash = Account.query.filter_by(code='110001').first()
            bank = Account.query.filter_by(code='110002').first()
            cash_balance = cash.get_balance() if cash else 0
            bank_balance = bank.get_balance() if bank else 0

            return render_template('financial/pay_salary.html',
                                   salary=salary,
                                   cash_balance=cash_balance,
                                   bank_balance=bank_balance,
                                   now=datetime.now())

        # ========== 3. تنفيذ الصرف (POST) ==========
        if salary.is_paid:
            flash('⚠️ هذا الراتب تم صرفه مسبقاً', 'warning')
            return redirect(url_for('salaries_list'))

        if salary.total_salary <= 0:
            flash('⚠️ لا يمكن صرف راتب بقيمة صفر أو أقل', 'danger')
            return redirect(url_for('salaries_list'))

        try:
            # الحصول على طريقة الدفع من النموذج
            payment_method = request.form.get('payment_method', 'cash')
            payment_reference = request.form.get('payment_reference', '')
            notes = request.form.get('notes', '')

            # البحث عن الحسابات
            salaries_payable = Account.query.filter_by(code='210001').first()
            if not salaries_payable:
                salaries_payable = Account(
                    code='210001',
                    name='Salaries Payable',
                    name_ar='الرواتب المستحقة',
                    account_type='liability',
                    nature='credit',
                    opening_balance=0,
                    is_active=True
                )
                db.session.add(salaries_payable)
                db.session.commit()

            # تحديد حساب الدفع
            if payment_method == 'bank_transfer':
                payment_account = Account.query.filter_by(code='110002').first()
                if not payment_account:
                    payment_account = Account(
                        code='110002',
                        name='Bank Account',
                        name_ar='البنك',
                        account_type='asset',
                        nature='debit',
                        opening_balance=0,
                        is_active=True
                    )
                    db.session.add(payment_account)
                    db.session.commit()

                # التحقق من رصيد البنك
                current_balance = payment_account.get_balance()
                if current_balance < salary.total_salary:
                    flash(f'⚠️ رصيد البنك غير كافٍ! المتوفر: {current_balance:,.2f} ريال', 'danger')
                    return redirect(url_for('pay_salary', salary_id=salary_id))
            else:
                payment_account = Account.query.filter_by(code='110001').first()
                if not payment_account:
                    payment_account = Account(
                        code='110001',
                        name='Cash',
                        name_ar='الصندوق',
                        account_type='asset',
                        nature='debit',
                        opening_balance=0,
                        is_active=True
                    )
                    db.session.add(payment_account)
                    db.session.commit()

                # التحقق من رصيد الصندوق
                current_balance = payment_account.get_balance()
                if current_balance < salary.total_salary:
                    flash(f'⚠️ رصيد الصندوق غير كافٍ! المتوفر: {current_balance:,.2f} ريال', 'danger')
                    flash('💡 يمكنك إيداع نقدي في الصندوق أولاً أو استخدام التحويل البنكي', 'warning')
                    return redirect(url_for('pay_salary', salary_id=salary_id))

            # تحديث بيانات الراتب
            salary.is_paid = True
            salary.paid_date = datetime.now().date()
            salary.payment_method = payment_method
            salary.payment_reference = payment_reference
            if notes:
                salary.notes = (salary.notes or '') + f'\nملاحظات الصرف: {notes}'

            # إنشاء قيد محاسبي لصرف الراتب
            entry_number = get_next_entry_number()

            journal_entry = JournalEntry(
                entry_number=entry_number,
                date=salary.paid_date,
                description=f'صرف راتب {salary.employee.name} عن {salary.notes or salary.month_year}',
                reference_type='salary_payment',
                reference_id=salary.id,
                created_by=current_user.id
            )
            db.session.add(journal_entry)
            db.session.flush()

            # تفصيل 1: مدين - الرواتب المستحقة (تخفيض الالتزام)
            detail1 = JournalEntryDetail(
                entry_id=journal_entry.id,
                account_id=salaries_payable.id,
                debit=salary.total_salary,
                credit=0,
                description=f'صرف راتب {salary.employee.name}'
            )
            db.session.add(detail1)

            # تفصيل 2: دائن - البنك/الصندوق
            detail2 = JournalEntryDetail(
                entry_id=journal_entry.id,
                account_id=payment_account.id,
                debit=0,
                credit=salary.total_salary,
                description=f'دفع الراتب عبر {payment_method}'
            )
            db.session.add(detail2)

            db.session.commit()

            flash(f'✅ تم دفع راتب {salary.employee.name} بمبلغ {salary.total_salary:,.0f} ريال بنجاح', 'success')
            flash(f'📋 قيد الصرف: {entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء صرف الراتب: {str(e)}', 'danger')
            import traceback
            traceback.print_exc()

        return redirect(url_for('salaries_list'))

    @app.route('/financial/salaries/bulk_pay', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def bulk_pay_salaries():
        """صرف رواتب متعددة دفعة واحدة"""
        try:
            data = request.get_json()
            salary_ids = data.get('salary_ids', [])
            payment_method = data.get('payment_method', 'bank_transfer')

            if not salary_ids:
                return jsonify({'success': False, 'error': 'لم يتم تحديد أي رواتب'})

            count = 0
            total_amount = 0
            skipped = 0

            for salary_id in salary_ids:
                salary = Salary.query.get(salary_id)
                if not salary:
                    continue

                if salary.is_paid:
                    skipped += 1
                    continue

                # منع صرف الرواتب الصفرية أو السالبة
                if salary.total_salary <= 0:
                    skipped += 1
                    continue

                salary.is_paid = True
                salary.paid_date = datetime.now().date()
                salary.payment_method = payment_method
                count += 1
                total_amount += salary.total_salary

            db.session.commit()

            message = f'✅ تم صرف {count} راتب بقيمة إجمالية {total_amount:,.0f} ريال'
            if skipped > 0:
                message += f' (تم تخطي {skipped} راتب غير صالح للصرف)'

            return jsonify({'success': True, 'message': message, 'count': count, 'total': total_amount})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    # ==================== المعاملات المالية (مع صلاحيات) ====================
    @app.route('/financial/transactions')
    @login_required
    @role_required('admin', 'finance', 'supervisor')
    def transactions_list():
        """عرض المعاملات المالية"""
        transaction_type = request.args.get('type', 'all')
        employee_id = request.args.get('employee_id', type=int)

        query = FinancialTransaction.query

        if transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)

        # تطبيق صلاحية المشرف (يرى فقط معاملات عمال شركته)
        if current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                worker_ids = [e.id for e in
                              Employee.query.filter_by(supervisor_id=supervisor_employee.id, is_active=True).all()]
                query = query.filter(FinancialTransaction.employee_id.in_(worker_ids))
            else:
                query = query.filter(False)

        if employee_id:
            query = query.filter_by(employee_id=employee_id)

        transactions = query.filter_by(is_settled=False).order_by(FinancialTransaction.date.desc()).all()
        employees = Employee.query.filter_by(is_active=True).all()

        return render_template('financial/transactions.html',
                               transactions=transactions,
                               employees=employees,
                               selected_type=transaction_type,
                               selected_employee=employee_id)

    @app.route('/financial/add_transaction', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_transaction():
        """إضافة معاملة مالية - بدون إنشاء قيد محاسبي فوري"""
        if request.method == 'POST':
            try:
                transaction = FinancialTransaction(
                    employee_id=request.form.get('employee_id'),
                    transaction_type=request.form.get('transaction_type'),
                    amount=float(request.form.get('amount')),
                    description=request.form.get('description'),
                    date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                    created_by=current_user.id,
                    is_settled=False,  # لم يتم ترحيلها بعد
                    journal_entry_id=None  # لا يوجد قيد محاسبي مرتبط بعد
                )
                db.session.add(transaction)
                db.session.commit()

                flash('✅ تم إضافة المعاملة المالية بنجاح (لم يتم ترحيلها إلى القيود المحاسبية بعد)', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')
                return redirect(url_for('add_transaction'))

            return redirect(url_for('transactions_list'))

        employees = Employee.query.filter_by(is_active=True).all()
        return render_template('financial/add_transaction.html',
                               employees=employees,
                               transaction_types=FinancialTransaction.TRANSACTION_TYPES)

    # ==================== إنشاء الفواتير الشهرية التلقائية للعقود السنوية ====================

    @app.route('/contracts/generate-monthly-invoices')
    @login_required
    @role_required('admin', 'finance')
    def generate_monthly_invoices():
        """إنشاء فواتير شهرية تلقائية للعقود السنوية النشطة"""
        from utils import create_contract_journal_entry

        today = datetime.now().date()
        current_month = today.strftime('%Y-%m')

        # البحث عن العقود النشطة
        active_contracts = Contract.query.filter(
            Contract.status == 'active',
            Contract.start_date <= today,
            (Contract.end_date >= today) | (Contract.end_date.is_(None))
        ).all()

        created_count = 0
        skipped_count = 0

        for contract in active_contracts:
            # تحديد قيمة القسط حسب نوع العقد
            if contract.contract_type == 'annual':
                monthly_amount = contract.contract_value / 12
            elif contract.contract_type == 'monthly':
                monthly_amount = contract.contract_value
            elif contract.contract_type == 'quarterly':
                monthly_amount = contract.contract_value / 3
            else:
                monthly_amount = contract.contract_value

            # تاريخ الفاتورة (أول يوم في الشهر الحالي)
            invoice_date = datetime(today.year, today.month, 1).date()

            # التحقق من عدم وجود قيد مسبق لنفس الشهر
            existing = JournalEntry.query.filter(
                JournalEntry.reference_type == 'contract',
                JournalEntry.reference_id == contract.id,
                JournalEntry.date >= invoice_date
            ).first()

            if existing:
                skipped_count += 1
                continue

            # ✅ إنشاء القيد المحاسبي باستخدام الدالة المصححة
            try:
                journal_entry = create_contract_journal_entry(contract)
                created_count += 1
                print(f"✅ تم إنشاء قيد للعقد {contract.id}: {journal_entry.entry_number}")
            except Exception as e:
                print(f"❌ خطأ في العقد {contract.id}: {e}")

        db.session.commit()

        flash(f'✅ تم إنشاء {created_count} قيد محاسبي للعقود', 'success')
        if skipped_count > 0:
            flash(f'⚠️ تم تخطي {skipped_count} عقد لوجود قيود سابقة', 'warning')

        return redirect(url_for('contracts_list'))

    @app.route('/contracts/auto-generate/<int:contract_id>')
    @login_required
    @role_required('admin', 'finance')
    def auto_generate_contract_invoices(contract_id):
        """إنشاء فواتير شهرية تلقائية لعقد سنوي محدد"""

        contract = Contract.query.get_or_404(contract_id)

        if contract.contract_type != 'annual':
            flash('⚠️ هذا العقد ليس سنوياً', 'warning')
            return redirect(url_for('contracts_list'))

        today = datetime.now().date()
        current_month = today.strftime('%Y-%m')

        # حساب قيمة الفاتورة الشهرية
        monthly_amount = contract.contract_value / 12

        # تاريخ الفاتورة (أول يوم في الشهر الحالي)
        invoice_date = datetime(today.year, today.month, 1).date()

        # تاريخ الاستحقاق (آخر يوم في الشهر)
        if today.month == 12:
            due_date = datetime(today.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            due_date = datetime(today.year, today.month + 1, 1).date() - timedelta(days=1)

        # التحقق من عدم وجود فاتورة لنفس الشهر
        existing = Invoice.query.filter(
            Invoice.contract_id == contract.id,
            Invoice.invoice_date >= invoice_date,
            Invoice.invoice_date <= due_date
        ).first()

        if existing:
            flash(f'⚠️ توجد فاتورة بالفعل للشهر {current_month}', 'warning')
            return redirect(url_for('contracts_list'))

        # إنشاء رقم فاتورة
        company_name = contract.company.name[:3] if contract.company else 'CON'
        invoice_number = f"INV-{company_name}-{current_month}"

        # إنشاء الفاتورة
        invoice = Invoice(
            contract_id=contract.id,
            invoice_number=invoice_number,
            amount=round(monthly_amount, 2),
            invoice_date=invoice_date,
            due_date=due_date,
            is_paid=False,
            paid_amount=0,
            notes=f"قسط شهري تلقائي - {current_month}"
        )
        db.session.add(invoice)
        db.session.flush()

        # إنشاء قيد محاسبي
        try:
            journal_entry = create_invoice_journal_entry(invoice)
            invoice.journal_entry_id = journal_entry.id
        except Exception as e:
            print(f"خطأ في القيد المحاسبي: {e}")

        db.session.commit()

        flash(f'✅ تم إنشاء فاتورة شهرية بقيمة {monthly_amount:,.0f} ريال', 'success')
        return redirect(url_for('invoices_list'))

    @app.route('/contracts/generate-all-future-invoices/<int:contract_id>')
    @login_required
    @role_required('admin', 'finance')
    def generate_all_future_invoices(contract_id):
        """إنشاء جميع الفواتير المستقبلية لعقد سنوي (حتى تاريخ الانتهاء)"""

        contract = Contract.query.get_or_404(contract_id)

        if contract.contract_type != 'annual':
            flash('⚠️ هذا العقد ليس سنوياً', 'warning')
            return redirect(url_for('contracts_list'))

        monthly_amount = contract.contract_value / 12

        # تحديد تاريخ البدء (الشهر الحالي)
        start_date = datetime.now().date()
        start_month = start_date.replace(day=1)

        # تحديد تاريخ الانتهاء
        end_date = contract.end_date or datetime(start_date.year + 1, start_date.month, 1).date()
        end_month = end_date.replace(day=1)

        created_count = 0
        current_date = start_month

        while current_date <= end_month:
            # تاريخ الفاتورة (أول يوم في الشهر)
            invoice_date = current_date

            # تاريخ الاستحقاق (آخر يوم في الشهر)
            if current_date.month == 12:
                due_date = datetime(current_date.year + 1, 1, 1).date() - timedelta(days=1)
            else:
                due_date = datetime(current_date.year, current_date.month + 1, 1).date() - timedelta(days=1)

            # التحقق من عدم وجود فاتورة
            existing = Invoice.query.filter(
                Invoice.contract_id == contract.id,
                Invoice.invoice_date >= invoice_date,
                Invoice.invoice_date <= due_date
            ).first()

            if not existing:
                invoice_number = f"INV-{contract.company.name[:3] if contract.company else 'CON'}-{current_date.strftime('%Y-%m')}"

                invoice = Invoice(
                    contract_id=contract.id,
                    invoice_number=invoice_number,
                    amount=round(monthly_amount, 2),
                    invoice_date=invoice_date,
                    due_date=due_date,
                    is_paid=False,
                    paid_amount=0,
                    notes=f"قسط شهري - {current_date.strftime('%B %Y')}"
                )
                db.session.add(invoice)
                created_count += 1

            # الانتقال إلى الشهر التالي
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1).date()
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1).date()

        db.session.commit()

        flash(f'✅ تم إنشاء {created_count} فاتورة مستقبلية', 'success')
        return redirect(url_for('contracts_list'))


    @app.route('/financial/delete_transaction/<int:trans_id>')
    @login_required
    @role_required('admin', 'finance')
    def delete_transaction(trans_id):
        """حذف معاملة مالية - فقط إذا لم يكن لها تأثير مالي"""
        transaction = FinancialTransaction.query.get_or_404(trans_id)

        # التحقق من إمكانية الحذف
        if not transaction.can_delete():
            if transaction.has_financial_impact():
                if transaction.is_settled:
                    flash('⚠️ لا يمكن حذف المعاملة لأنها تم ترحيلها إلى الراتب بالفعل', 'danger')
                elif transaction.journal_entry_id:
                    flash('⚠️ لا يمكن حذف المعاملة لأن لها قيد محاسبي مرتبط', 'danger')
                else:
                    flash('⚠️ لا يمكن حذف هذه المعاملة لأن لها تأثير مالي', 'danger')
            else:
                flash('⚠️ لا يمكن حذف هذه المعاملة', 'danger')
            return redirect(url_for('transactions_list'))

        try:
            db.session.delete(transaction)
            db.session.commit()
            flash('✅ تم حذف المعاملة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

        return redirect(url_for('transactions_list'))

    @app.route('/financial/transfer_to_salary', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def transfer_transaction_to_salary():
        """ترحيل معاملة واحدة إلى الراتب - إنشاء قيد محاسبي"""
        try:
            data = request.get_json()
            transaction_id = data.get('transaction_id')

            transaction = FinancialTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'error': 'المعاملة غير موجودة'})

            if transaction.is_settled:
                return jsonify({'success': False, 'error': 'المعاملة تم ترحيلها مسبقاً'})

            if transaction.journal_entry_id:
                return jsonify({'success': False, 'error': 'المعاملة لها قيد محاسبي مرتبط بالفعل'})

            # إنشاء قيد محاسبي للمعاملة
            journal_entry = create_transaction_journal_entry(transaction)

            if journal_entry:
                transaction.is_settled = True
                transaction.settled_date = datetime.now().date()
                transaction.journal_entry_id = journal_entry.id
                db.session.commit()
                return jsonify({'success': True, 'message': 'تم ترحيل المعاملة وإنشاء القيد المحاسبي بنجاح'})
            else:
                return jsonify({'success': False, 'error': 'فشل في إنشاء القيد المحاسبي'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/financial/transfer_to_preparation', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def transfer_transaction_to_preparation():
        """ترحيل معاملة مالية إلى تحضير الدوام"""
        try:
            data = request.get_json()
            transaction_id = data.get('transaction_id')
            prep_id = data.get('prep_id')

            transaction = FinancialTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'error': 'المعاملة غير موجودة'})

            if transaction.is_settled:
                return jsonify({'success': False, 'error': 'المعاملة تم ترحيلها مسبقاً'})

            preparation = AttendancePreparation.query.get(prep_id)
            if not preparation or preparation.is_processed:
                return jsonify({'success': False, 'error': 'تحضير الدوام غير صالح للترحيل'})

            # إضافة المعاملة إلى تحضير الدوام (يمكن إضافتها كحقل في جدول التفاصيل)
            # أو وضع علامة بأنها مرتبطة بالتحضير

            return jsonify({'success': True, 'message': 'تم إضافة المعاملة إلى تحضير الدوام'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/financial/bulk_transfer', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def bulk_transfer_transactions():
        """ترحيل معاملات متعددة إلى الراتب"""
        try:
            data = request.get_json()
            transaction_ids = data.get('transaction_ids', [])

            if not transaction_ids:
                return jsonify({'success': False, 'error': 'لم يتم تحديد أي معاملات'})

            count = 0
            for trans_id in transaction_ids:
                transaction = FinancialTransaction.query.get(trans_id)
                if transaction and not transaction.is_settled:
                    transaction.is_settled = True
                    transaction.settled_date = datetime.now().date()
                    count += 1

            db.session.commit()

            return jsonify({'success': True, 'message': f'تم ترحيل {count} معاملة بنجاح'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    # ==================== واجهات رئيسية ====================
    @app.route('/financial/dashboard')
    @login_required
    @role_required('admin', 'finance')
    def financial_dashboard():
        """لوحة المالية الرئيسية - للمدير والموظف المالي فقط"""
        from sqlalchemy import func

        total_advances = FinancialTransaction.query.filter_by(transaction_type='advance', is_settled=False).count()
        total_overtime = FinancialTransaction.query.filter_by(transaction_type='overtime', is_settled=False).count()
        total_deductions = FinancialTransaction.query.filter_by(transaction_type='deduction', is_settled=False).count()
        total_salaries = Salary.query.filter_by(is_paid=False).count()

        recent_transactions = FinancialTransaction.query.order_by(FinancialTransaction.date.desc()).limit(10).all()
        recent_salaries = Salary.query.order_by(Salary.month_year.desc()).limit(10).all()

        return render_template('financial/dashboard.html',
                               total_advances=total_advances,
                               total_overtime=total_overtime,
                               total_deductions=total_deductions,
                               total_salaries=total_salaries,
                               recent_transactions=recent_transactions,
                               recent_salaries=recent_salaries)

    # ==================== العقود والفواتير (مع صلاحيات) ====================
    @app.route('/contracts')
    @login_required
    @role_required('admin', 'finance')
    def contracts_list():
        """عرض العقود"""
        if current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                contracts = Contract.query.filter_by(company_id=supervisor_employee.company_id).all()
            else:
                contracts = []
        else:
            contracts = Contract.query.all()
        return render_template('contracts/contracts.html', contracts=contracts)

    @app.route('/contracts/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_contract():
        """إضافة عقد - للمدير والموظف المالي فقط"""
        if request.method == 'POST':
            contract = Contract(
                company_id=request.form.get('company_id'),
                contract_type=request.form.get('contract_type'),
                contract_value=float(request.form.get('contract_value')),
                start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get(
                    'end_date') else None,
                notes=request.form.get('notes')
            )
            contract.remaining_amount = contract.contract_value
            db.session.add(contract)
            db.session.commit()
            flash('تم إضافة العقد بنجاح', 'success')
            return redirect(url_for('contracts_list'))

        companies = Company.query.all()
        return render_template('contracts/add_contract.html', companies=companies)

    @app.route('/invoices')
    @login_required
    @role_required('admin', 'finance')
    def invoices_list():
        """عرض الفواتير"""
        if current_user.role == 'supervisor':
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee:
                contracts = Contract.query.filter_by(company_id=supervisor_employee.company_id).all()
                contract_ids = [c.id for c in contracts]
                invoices = Invoice.query.filter(Invoice.contract_id.in_(contract_ids)).all()
            else:
                invoices = []
        else:
            invoices = Invoice.query.all()
        return render_template('contracts/invoices.html', invoices=invoices)

    @app.route('/invoices/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_invoice():
        """إضافة فاتورة - للمدير والموظف المالي فقط"""
        if request.method == 'POST':
            try:
                invoice = Invoice(
                    contract_id=request.form.get('contract_id'),
                    invoice_number=request.form.get('invoice_number'),
                    amount=float(request.form.get('amount')),
                    invoice_date=datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date(),
                    due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get(
                        'due_date') else None,
                    notes=request.form.get('notes')
                )
                db.session.add(invoice)
                db.session.flush()

                contract = Contract.query.get(request.form.get('contract_id'))
                if contract:
                    contract.amount_received += invoice.amount
                    contract.remaining_amount = contract.contract_value - contract.amount_received
                    if contract.remaining_amount <= 0:
                        contract.status = 'completed'

                # إنشاء قيد محاسبي للفاتورة وربطه
                try:
                    journal_entry = create_invoice_journal_entry(invoice)
                    invoice.journal_entry_id = journal_entry.id
                    invoice.is_posted_to_accounts = True
                except Exception as je:
                    db.session.rollback()
                    flash(f'تمت إضافة الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                    return redirect(url_for('invoices_list'))

                db.session.commit()
                flash('✅ تم إضافة الفاتورة والقيد المحاسبي بنجاح', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')
                return redirect(url_for('add_invoice'))

            return redirect(url_for('invoices_list'))

        contracts = Contract.query.filter_by(status='active').all()
        return render_template('contracts/add_invoice.html', contracts=contracts)

    # ==================== تعديل وحذف الفواتير ====================

    @app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def edit_invoice(invoice_id):
        """تعديل فاتورة"""
        invoice = Invoice.query.get_or_404(invoice_id)

        if request.method == 'POST':
            try:
                # تحديث بيانات الفاتورة
                invoice.invoice_number = request.form.get('invoice_number')
                invoice.amount = float(request.form.get('amount'))
                invoice.invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()

                if request.form.get('due_date'):
                    invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
                else:
                    invoice.due_date = None

                invoice.notes = request.form.get('notes')

                # تحديث العقد المرتبط
                new_contract_id = request.form.get('contract_id')
                if new_contract_id and int(new_contract_id) != invoice.contract_id:
                    # إعادة حساب المبالغ للعقد القديم
                    old_contract = Contract.query.get(invoice.contract_id)
                    if old_contract:
                        old_contract.amount_received -= invoice.amount
                        old_contract.remaining_amount = old_contract.contract_value - old_contract.amount_received
                        if old_contract.remaining_amount > 0:
                            old_contract.status = 'active'
                        elif old_contract.remaining_amount == 0:
                            old_contract.status = 'completed'

                    # تحديث العقد الجديد
                    invoice.contract_id = int(new_contract_id)
                    new_contract = Contract.query.get(invoice.contract_id)
                    if new_contract:
                        new_contract.amount_received += invoice.amount
                        new_contract.remaining_amount = new_contract.contract_value - new_contract.amount_received
                        if new_contract.remaining_amount <= 0:
                            new_contract.status = 'completed'
                else:
                    # تحديث المبلغ في نفس العقد
                    contract = Contract.query.get(invoice.contract_id)
                    if contract:
                        # إعادة حساب إجمالي الفواتير لهذا العقد
                        total_invoices = sum(i.amount for i in contract.invoices if i.id != invoice.id) + invoice.amount
                        contract.amount_received = total_invoices
                        contract.remaining_amount = contract.contract_value - total_invoices
                        if contract.remaining_amount <= 0:
                            contract.status = 'completed'
                        elif contract.status == 'completed':
                            contract.status = 'active'

                db.session.commit()
                flash('✅ تم تحديث الفاتورة بنجاح', 'success')
                return redirect(url_for('invoices_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        contracts = Contract.query.all()
        return render_template('contracts/edit_invoice.html',
                               invoice=invoice,
                               contracts=contracts,
                               now=datetime.now())

    @app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def delete_invoice(invoice_id):
        """حذف فاتورة - فقط إذا لم يكن لها تأثير مالي"""
        invoice = Invoice.query.get_or_404(invoice_id)

        # التحقق من إمكانية الحذف
        if not invoice.can_delete():
            if invoice.has_financial_impact():
                if invoice.has_journal_entry():
                    flash('⚠️ لا يمكن حذف الفاتورة لأن لها قيد محاسبي مرتبط', 'danger')
                elif invoice.paid_amount > 0:
                    flash(f'⚠️ لا يمكن حذف الفاتورة لأن تم دفع {invoice.paid_amount:,.0f} ريال منها', 'danger')
                else:
                    flash('⚠️ لا يمكن حذف هذه الفاتورة لأن لها تأثير مالي', 'danger')
            else:
                flash('⚠️ لا يمكن حذف هذه الفاتورة', 'danger')
            return redirect(url_for('invoices_list'))

        try:
            # تحديث العقد المرتبط
            contract = Contract.query.get(invoice.contract_id)
            if contract:
                contract.amount_received -= invoice.amount
                contract.remaining_amount = contract.contract_value - contract.amount_received
                if contract.remaining_amount > 0:
                    contract.status = 'active'
                elif contract.remaining_amount == 0:
                    contract.status = 'completed'

            db.session.delete(invoice)
            db.session.commit()
            flash('✅ تم حذف الفاتورة بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

        return redirect(url_for('invoices_list'))

    @app.route('/invoices/pay/<int:invoice_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def pay_invoice(invoice_id):
        """تسديد فاتورة - للمدير والموظف المالي فقط"""
        invoice = Invoice.query.get_or_404(invoice_id)

        if request.method == 'POST':
            try:
                paid_amount = float(request.form.get('paid_amount', 0))
                payment_method = request.form.get('payment_method')
                payment_reference = request.form.get('payment_reference')
                notes = request.form.get('notes', '')

                remaining = invoice.amount - invoice.paid_amount
                if paid_amount <= 0:
                    flash('المبلغ المدفوع يجب أن يكون أكبر من صفر', 'danger')
                    return redirect(url_for('pay_invoice', invoice_id=invoice_id))

                if paid_amount > remaining:
                    flash('المبلغ المدفوع يتجاوز المبلغ المتبقي', 'danger')
                    return redirect(url_for('pay_invoice', invoice_id=invoice_id))

                invoice.paid_amount += paid_amount
                invoice.payment_method = payment_method
                invoice.payment_reference = payment_reference
                invoice.notes = notes + (
                    f'\nتسديد بتاريخ {datetime.now().strftime("%Y-%m-%d")}' if invoice.notes else f'تسديد بتاريخ {datetime.now().strftime("%Y-%m-%d")}')

                if invoice.paid_amount >= invoice.amount:
                    invoice.is_paid = True
                    invoice.paid_date = datetime.now().date()
                    flash('تم تسديد كامل قيمة الفاتورة بنجاح', 'success')
                else:
                    flash(
                        f'تم تسديد مبلغ {paid_amount:,.0f} ريال، المتبقي {invoice.amount - invoice.paid_amount:,.0f} ريال',
                        'success')

                contract = invoice.contract
                if contract:
                    total_paid = sum(i.paid_amount for i in contract.invoices)
                    contract.amount_received = total_paid
                    contract.remaining_amount = contract.contract_value - total_paid
                    if contract.remaining_amount <= 0:
                        contract.status = 'completed'
                    elif contract.status == 'completed':
                        contract.status = 'active'

                # إنشاء قيد محاسبي للتسديد
                try:
                    create_invoice_payment_journal_entry(invoice, paid_amount, payment_method)
                except Exception as je:
                    db.session.rollback()
                    flash(f'تم تسديد الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                    return redirect(url_for('invoices_list'))

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ: {str(e)}', 'danger')

            return redirect(url_for('invoices_list'))

        remaining_amount = invoice.amount - (invoice.paid_amount or 0)
        return render_template('contracts/pay_invoice.html',
                               invoice=invoice,
                               remaining_amount=remaining_amount,
                               now=datetime.now())

    @app.route('/invoices/print/<int:invoice_id>')
    @login_required
    def print_invoice(invoice_id):
        """طباعة الفاتورة"""
        invoice = Invoice.query.get_or_404(invoice_id)

        company_info = {
            'name': 'طلعت هائل للخدمات والاستشارات الزراعية',
            'name_en': 'TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS',
            'address': 'الجمهورية اليمنية - محافظة الحديدة',
            'phone': '+967 xxx xxx xxx',
            'email': 'info@talaathail.com',
            'tax_number': '123456789'
        }

        return render_template('contracts/print_invoice.html',
                               invoice=invoice,
                               company_info=company_info,
                               now=datetime.now())

    @app.route('/accounts')
    @login_required
    @role_required('admin', 'finance')
    def accounts_dashboard():
        """لوحة التحكم الرئيسية لنظام الحسابات"""
        from sqlalchemy import func

        # إحصائيات الحسابات
        accounts_count = Account.query.filter_by(is_active=True).count()
        journal_entries_count = JournalEntry.query.count()

        # حساب إجمالي الأصول
        assets = Account.query.filter_by(account_type='asset', is_active=True).all()
        total_assets = sum(a.get_balance() for a in assets)

        # حساب صافي الأرباح (الإيرادات - المصروفات)
        revenues = Account.query.filter_by(account_type='revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='expense', is_active=True).all()
        total_revenue = sum(r.get_balance() for r in revenues)
        total_expense = sum(e.get_balance() for e in expenses)
        net_income = total_revenue - total_expense

        return render_template('accounts/dashboard.html',
                               accounts_count=accounts_count,
                               journal_entries_count=journal_entries_count,
                               total_assets=total_assets,
                               net_income=net_income,
                               now=datetime.now())

    # ==================== إدارة الحسابات (دليل الحسابات) ====================

    @app.route('/accounts/chart')
    @login_required
    @role_required('admin', 'finance')
    def chart_of_accounts():
        """عرض دليل الحسابات"""
        accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()

        # بناء هيكل شجري
        def build_tree(parent_id=None, level=0):
            tree = []
            for acc in accounts:
                if acc.parent_id == parent_id:
                    acc.level = level
                    acc.children = build_tree(acc.id, level + 1)
                    tree.append(acc)
            return tree

        account_tree = build_tree()

        return render_template('accounts/chart_of_accounts.html',
                               accounts=account_tree,
                               account_types=Account.ACCOUNT_TYPES,
                               now=datetime.now())

    @app.route('/accounts/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def add_account():
        """إضافة حساب جديد"""
        if request.method == 'POST':
            try:
                # التحقق من عدم وجود حساب بنفس الرقم
                existing = Account.query.filter_by(code=request.form.get('code')).first()
                if existing:
                    flash('⚠️ رقم الحساب موجود مسبقاً', 'danger')
                    return redirect(url_for('add_account'))

                account = Account(
                    code=request.form.get('code'),
                    name=request.form.get('name'),
                    name_ar=request.form.get('name_ar'),
                    account_type=request.form.get('account_type'),
                    nature=request.form.get('nature'),
                    parent_id=request.form.get('parent_id') or None,
                    opening_balance=float(request.form.get('opening_balance', 0)),
                    is_active=True,
                    notes=request.form.get('notes')
                )
                db.session.add(account)
                db.session.commit()
                flash(f'✅ تم إضافة الحساب {account.code} - {account.name_ar} بنجاح', 'success')
                return redirect(url_for('chart_of_accounts'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        # GET request
        parent_accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
        return render_template('accounts/add_account.html',
                               parent_accounts=parent_accounts,
                               account_types=Account.ACCOUNT_TYPES,
                               natures={'debit': 'مدين', 'credit': 'دائن'},
                               now=datetime.now())

    @app.route('/accounts/edit/<int:account_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def edit_account(account_id):
        """تعديل حساب"""
        account = Account.query.get_or_404(account_id)

        if request.method == 'POST':
            try:
                # التحقق من عدم وجود حساب بنفس الرقم (لحسابات أخرى)
                existing = Account.query.filter(
                    Account.code == request.form.get('code'),
                    Account.id != account_id
                ).first()
                if existing:
                    flash('⚠️ رقم الحساب موجود مسبقاً لحساب آخر', 'danger')
                    return redirect(url_for('edit_account', account_id=account_id))

                account.code = request.form.get('code')
                account.name = request.form.get('name')
                account.name_ar = request.form.get('name_ar')
                account.account_type = request.form.get('account_type')
                account.nature = request.form.get('nature')
                account.parent_id = request.form.get('parent_id') or None
                account.notes = request.form.get('notes')

                # فقط المسموح بتعديل الرصيد الافتتاحي
                if 'opening_balance' in request.form:
                    account.opening_balance = float(request.form.get('opening_balance', 0))

                db.session.commit()
                flash(f'✅ تم تعديل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
                return redirect(url_for('chart_of_accounts'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        # GET request
        parent_accounts = Account.query.filter(
            Account.is_active == True,
            Account.id != account_id
        ).order_by(Account.code).all()

        return render_template('accounts/edit_account.html',
                               account=account,
                               parent_accounts=parent_accounts,
                               account_types=Account.ACCOUNT_TYPES,
                               natures={'debit': 'مدين', 'credit': 'دائن'},
                               now=datetime.now())

    @app.route('/accounts/delete/<int:account_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_account(account_id):
        """حذف حساب (تعطيل فقط) - مع التحقق من عدم ارتباطه بمعاملات"""
        account = Account.query.get_or_404(account_id)

        # التحقق من وجود معاملات مرتبطة بالحساب
        from models import JournalEntryDetail, FinancialTransaction, Salary, Invoice, SupplierInvoice

        # 1. التحقق من القيود المحاسبية
        journal_entries = JournalEntryDetail.query.filter_by(account_id=account.id).count()
        if journal_entries > 0:
            flash(
                f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بـ {journal_entries} قيد محاسبي',
                'danger')
            return redirect(url_for('chart_of_accounts'))

        # 2. التحقق من المعاملات المالية
        transactions = FinancialTransaction.query.filter_by(employee_id=account.id).count()
        if transactions > 0:
            flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بمعاملات مالية', 'danger')
            return redirect(url_for('chart_of_accounts'))

        # 3. التحقق من الفواتير
        invoices = Invoice.query.filter_by(contract_id=account.id).count()
        if invoices > 0:
            flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بفواتير', 'danger')
            return redirect(url_for('chart_of_accounts'))

        # 4. التحقق من فواتير الموردين
        supplier_invoices = SupplierInvoice.query.filter_by(supplier_id=account.id).count()
        if supplier_invoices > 0:
            flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بفواتير موردين', 'danger')
            return redirect(url_for('chart_of_accounts'))

        # 5. التحقق من وجود حسابات فرعية
        children = Account.query.filter_by(parent_id=account.id, is_active=True).count()
        if children > 0:
            flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه يحتوي على {children} حسابات فرعية',
                  'danger')
            return redirect(url_for('chart_of_accounts'))

        # تعطيل الحساب بدلاً من حذفه
        account.is_active = False
        db.session.commit()

        flash(f'✅ تم تعطيل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
        return redirect(url_for('chart_of_accounts'))

    @app.route('/accounts/activate/<int:account_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def activate_account(account_id):
        """تفعيل حساب معطل"""
        account = Account.query.get_or_404(account_id)
        account.is_active = True
        db.session.commit()
        flash(f'✅ تم تفعيل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
        return redirect(url_for('chart_of_accounts'))


    @app.route('/accounts/journal')
    @login_required
    @role_required('admin', 'finance')
    def journal_entries_list():
        """عرض القيود اليومية"""
        from models import Account

        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = JournalEntry.query

        if start_date:
            query = query.filter(JournalEntry.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(JournalEntry.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

        entries = query.order_by(JournalEntry.date.desc(), JournalEntry.entry_number.desc()).all()

        # التحقق من وجود قيود عكسية لكل قيد
        for entry in entries:
            entry.has_reverse = JournalEntry.query.filter(
                JournalEntry.reference_type == 'reverse',
                JournalEntry.reference_id == entry.id
            ).first() is not None

        # ✅ حساب الإجماليات في الباكند
        total_debit = sum(entry.get_total_debit() for entry in entries)
        total_credit = sum(entry.get_total_credit() for entry in entries)

        # جلب الحسابات لإضافة قيد جديد
        accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()

        return render_template('accounts/journal_entries.html',
                               entries=entries,
                               accounts=accounts,
                               total_debit=total_debit,
                               total_credit=total_credit,
                               start_date=start_date,
                               end_date=end_date)

    @app.route('/accounts/journal/add', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_journal_entry():
        """إضافة قيد يومي جديد"""
        from utils import create_journal_entry

        try:
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            description = request.form.get('description')
            reference_type = request.form.get('reference_type') or None

            # جمع تفاصيل القيد من النموذج
            account_ids = request.form.getlist('account_id[]')
            debits = request.form.getlist('debit[]')
            credits = request.form.getlist('credit[]')

            entries = []
            for i in range(len(account_ids)):
                if account_ids[i] and (float(debits[i]) > 0 or float(credits[i]) > 0):
                    entries.append((
                        int(account_ids[i]),
                        float(debits[i]),
                        float(credits[i]),
                        f'سطر {i + 1}'
                    ))

            if not entries:
                flash('⚠️ يجب إضافة至少 سطر واحد للقيد', 'danger')
                return redirect(url_for('journal_entries_list'))

            # إنشاء القيد
            journal_entry = create_journal_entry(
                date=date,
                description=description,
                entries=entries,
                reference_type=reference_type,
                reference_id=None
            )

            flash(f'✅ تم إضافة القيد {journal_entry.entry_number} بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('journal_entries_list'))

    @app.route('/accounts/reverse_entry/<int:entry_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def reverse_journal_entry_view(entry_id):
        """عكس قيد محاسبي"""
        from utils import reverse_journal_entry

        original_entry = JournalEntry.query.get_or_404(entry_id)

        # التحقق من عدم عكس القيد مسبقاً
        reversed_exists = JournalEntry.query.filter(
            JournalEntry.reference_type == 'reverse',
            JournalEntry.reference_id == original_entry.id
        ).first()

        if reversed_exists:
            flash(f'⚠️ هذا القيد تم عكسه مسبقاً في القيد رقم: {reversed_exists.entry_number}', 'warning')
            return redirect(url_for('journal_entries_list'))

        try:
            # إنشاء قيد عكسي
            reverse_entry = reverse_journal_entry(original_entry.id)

            flash(f'✅ تم عكس القيد {original_entry.entry_number} بنجاح', 'success')
            flash(f'📋 القيد العكسي: {reverse_entry.entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

        return redirect(url_for('journal_entries_list'))

    @app.route('/accounts/transfer', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def transfer_between_accounts():
        """نقل مبلغ من حساب إلى حساب آخر"""
        from utils import create_journal_entry
        from models import Account
        from datetime import datetime

        try:
            from_account_id = int(request.form.get('from_account_id'))
            to_account_id = int(request.form.get('to_account_id'))
            amount = float(request.form.get('amount'))
            description = request.form.get('description')

            from_account = Account.query.get(from_account_id)
            to_account = Account.query.get(to_account_id)

            if not from_account or not to_account:
                flash('❌ الحسابات غير موجودة', 'danger')
                return redirect(url_for('journal_entries_list'))

            if from_account_id == to_account_id:
                flash('⚠️ لا يمكن التحويل لنفس الحساب', 'danger')
                return redirect(url_for('journal_entries_list'))

            # ✅ التحقق الصحيح من الرصيد
            if from_account.nature == 'debit':
                current_balance = from_account.get_balance()
                if current_balance < amount:
                    flash(f'⚠️ الرصيد غير كافٍ في حساب {from_account.name_ar}. المتوفر: {current_balance:,.2f}',
                          'danger')
                    return redirect(url_for('journal_entries_list'))

            # ✅ القيد الصحيح للتحويل
            entries = [
                (to_account.id, amount, 0, f'استلام من {from_account.name_ar}'),  # مدين (يزيد)
                (from_account.id, 0, amount, f'تحويل إلى {to_account.name_ar}')  # دائن (ينقص)
            ]

            journal_entry = create_journal_entry(
                date=datetime.now().date(),
                description=f'تحويل: {description} - من {from_account.name_ar} إلى {to_account.name_ar}',
                entries=entries,
                reference_type='transfer',
                reference_id=None
            )

            flash(f'✅ تم تحويل {amount:,.2f} ريال من {from_account.name_ar} إلى {to_account.name_ar}', 'success')
            flash(f'📋 رقم القيد: {journal_entry.entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('journal_entries_list'))

    @app.route('/api/journal-entry/<int:entry_id>')
    @login_required
    def get_journal_entry_api(entry_id):
        """API لجلب تفاصيل القيد"""
        entry = JournalEntry.query.get_or_404(entry_id)
        details = []
        for detail in entry.details:
            account = Account.query.get(detail.account_id)
            details.append({
                'account_code': account.code if account else '-',
                'account_name': f"{account.code} - {account.name_ar}" if account else '-',
                'debit': f"{detail.debit:,.2f}",
                'credit': f"{detail.credit:,.2f}"
            })
        return jsonify({
            'entry_number': entry.entry_number,
            'date': entry.date.strftime('%Y-%m-%d'),
            'description': entry.description,
            'details': details
        })

    @app.route('/accounts/zero-out', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def zero_out_account():
        """تصفير حساب (نقل رصيده بالكامل إلى حساب آخر)"""
        from utils import create_journal_entry
        from models import Account

        try:
            account_id = int(request.form.get('account_id'))
            target_account_id = int(request.form.get('target_account_id'))

            account = Account.query.get(account_id)
            target_account = Account.query.get(target_account_id)

            if not account or not target_account:
                flash('❌ الحسابات غير موجودة', 'danger')
                return redirect(url_for('journal_entries_list'))

            if account_id == target_account_id:
                flash('⚠️ لا يمكن تصفير الحساب لنفسه', 'danger')
                return redirect(url_for('journal_entries_list'))

            # الحصول على الرصيد الحالي
            current_balance = account.get_balance()

            if current_balance == 0:
                flash(f'⚠️ حساب {account.name_ar} رصيده صفر بالفعل', 'warning')
                return redirect(url_for('journal_entries_list'))

            amount = abs(current_balance)

            # تحديد طبيعة القيد حسب نوع الحساب
            if account.nature == 'debit' and current_balance > 0:
                # حساب مدين برصيد موجب: نقل المدين
                entries = [
                    (account.id, amount, 0, f'تصفير حساب {account.name_ar}'),
                    (target_account.id, 0, amount, f'استلام رصيد من {account.name_ar}')
                ]
                description = f'تصفير حساب {account.name_ar} (رصيد مدين {amount:,.2f}) إلى {target_account.name_ar}'
            elif account.nature == 'debit' and current_balance < 0:
                # حساب مدين برصيد سالب (دائن): نقل الدائن
                entries = [
                    (account.id, 0, amount, f'تصفير حساب {account.name_ar}'),
                    (target_account.id, amount, 0, f'تحويل رصيد من {account.name_ar}')
                ]
                description = f'تصفير حساب {account.name_ar} (رصيد دائن {amount:,.2f}) إلى {target_account.name_ar}'
            elif account.nature == 'credit' and current_balance > 0:
                # حساب دائن برصيد موجب
                entries = [
                    (account.id, 0, amount, f'تصفير حساب {account.name_ar}'),
                    (target_account.id, amount, 0, f'تحويل رصيد من {account.name_ar}')
                ]
                description = f'تصفير حساب {account.name_ar} (رصيد دائن {amount:,.2f}) إلى {target_account.name_ar}'
            else:
                # حساب دائن برصيد سالب
                entries = [
                    (account.id, amount, 0, f'تصفير حساب {account.name_ar}'),
                    (target_account.id, 0, amount, f'استلام رصيد من {account.name_ar}')
                ]
                description = f'تصفير حساب {account.name_ar} (رصيد مدين {amount:,.2f}) إلى {target_account.name_ar}'

            # إنشاء قيد التسوية
            journal_entry = create_journal_entry(
                date=datetime.now().date(),
                description=description,
                entries=entries,
                reference_type='zero_out',
                reference_id=None
            )

            flash(f'✅ تم تصفير حساب {account.name_ar}', 'success')
            flash(f'💰 تم نقل {amount:,.2f} ريال إلى {target_account.name_ar}', 'info')
            flash(f'📋 رقم القيد: {journal_entry.entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('journal_entries_list'))

    @app.route('/accounts/transfer-history')
    @login_required
    @role_required('admin', 'finance')
    def transfer_history():
        """عرض سجل التحويلات بين الحسابات"""
        transfers = JournalEntry.query.filter(
            JournalEntry.reference_type.in_(['transfer', 'zero_out'])
        ).order_by(JournalEntry.date.desc()).all()

        return render_template('accounts/transfer_history.html', transfers=transfers)

    @app.route('/financial/cash/settle', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def settle_cash():
        """تسوية رصيد الصندوق - إيداع أو سحب"""
        from models import Account, JournalEntry, JournalEntryDetail
        from datetime import datetime
        from utils import create_journal_entry, get_next_entry_number

        # التأكد من وجود حساب الصندوق
        cash_account = Account.query.filter_by(code='110001').first()
        if not cash_account:
            cash_account = Account(
                code='110001', name='Cash', name_ar='الصندوق',
                account_type='asset', nature='debit', opening_balance=0, is_active=True
            )
            db.session.add(cash_account)
            db.session.commit()

        # جلب آخر عمليات الصندوق
        cash_entries = JournalEntry.query.filter(
            JournalEntry.reference_type.in_(['cash_deposit', 'cash_withdraw', 'adjustment'])
        ).order_by(JournalEntry.date.desc()).limit(20).all()

        if request.method == 'POST':
            try:
                transaction_type = request.form.get('transaction_type')
                amount = float(request.form.get('amount'))
                description = request.form.get('description')

                if amount <= 0:
                    flash('⚠️ المبلغ يجب أن يكون أكبر من صفر', 'danger')
                    return redirect(url_for('settle_cash'))

                if transaction_type == 'deposit':
                    # إيداع: زيادة الصندوق
                    # الحصول على حساب رأس المال أو الأرباح المحتجزة
                    equity_account = Account.query.filter_by(code='310001').first()
                    if not equity_account:
                        equity_account = Account.query.filter_by(code='320001').first()

                    if not equity_account:
                        equity_account = Account(
                            code='310001', name='Capital', name_ar='رأس المال',
                            account_type='equity', nature='credit', opening_balance=0, is_active=True
                        )
                        db.session.add(equity_account)
                        db.session.commit()

                    entries = [
                        (cash_account.id, amount, 0, f'إيداع نقدي: {description}'),
                        (equity_account.id, 0, amount, 'مقابل الإيداع')
                    ]
                    reference_type = 'cash_deposit'
                    flash_msg = f'✅ تم إيداع {amount:,.2f} ريال في الصندوق'

                else:  # withdraw
                    # سحب: تخفيض الصندوق
                    current_balance = cash_account.get_balance()
                    if current_balance < amount:
                        flash(f'⚠️ الرصيد غير كافٍ. المتوفر: {current_balance:,.2f} ريال', 'danger')
                        return redirect(url_for('settle_cash'))

                    # الحصول على حساب المصروفات
                    expense_account = Account.query.filter_by(code='530005').first()
                    if not expense_account:
                        expense_account = Account(
                            code='530005', name='General Expense', name_ar='مصروفات عامة',
                            account_type='expense', nature='debit', opening_balance=0, is_active=True
                        )
                        db.session.add(expense_account)
                        db.session.commit()

                    entries = [
                        (cash_account.id, 0, amount, f'سحب نقدي: {description}'),
                        (expense_account.id, amount, 0, 'مقابل السحب')
                    ]
                    reference_type = 'cash_withdraw'
                    flash_msg = f'✅ تم سحب {amount:,.2f} ريال من الصندوق'

                # إنشاء القيد المحاسبي
                journal_entry = create_journal_entry(
                    date=datetime.now().date(),
                    description=f'تسوية الصندوق: {description}',
                    entries=entries,
                    reference_type=reference_type,
                    reference_id=None
                )

                flash(flash_msg, 'success')
                flash(f'📋 رقم القيد: {journal_entry.entry_number}', 'info')

            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطأ: {str(e)}', 'danger')

            return redirect(url_for('settle_cash'))

        # GET request
        current_balance = cash_account.get_balance()
        return render_template('financial/settle_cash.html',
                               cash_balance=current_balance,
                               cash_entries=cash_entries,
                               now=datetime.now())



    def get_equity_account():
        """الحصول على حساب حقوق الملكية (رأس المال أو الأرباح المحتجزة)"""
        equity = Account.query.filter_by(code='310001').first()
        if not equity:
            equity = Account(
                code='310001', name='Capital', name_ar='رأس المال',
                account_type='equity', nature='credit', opening_balance=0, is_active=True
            )
            db.session.add(equity)
            db.session.commit()
        return equity

    def get_expense_account():
        """الحصول على حساب المصروفات العامة"""
        expense = Account.query.filter_by(code='530005').first()
        if not expense:
            expense = Account(
                code='530005', name='General Expense', name_ar='مصروفات عامة',
                account_type='expense', nature='debit', opening_balance=0, is_active=True
            )
            db.session.add(expense)
            db.session.commit()
        return expense

    @app.route('/accounts/trial_balance')
    @login_required
    @role_required('admin', 'finance')
    def trial_balance():
        """ميزان المراجعة"""
        as_of_date = request.args.get('as_of_date')

        if not as_of_date:
            as_of_date = datetime.now().date()
        else:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

        accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()

        trial_balance_data = []
        total_debit = 0
        total_credit = 0

        for account in accounts:
            balance = account.get_balance(as_of_date)

            if account.nature == 'debit':
                debit = balance if balance > 0 else 0
                credit = abs(balance) if balance < 0 else 0
            else:
                credit = balance if balance > 0 else 0
                debit = abs(balance) if balance < 0 else 0

            total_debit += debit
            total_credit += credit

            trial_balance_data.append({
                'account': account,
                'opening_balance': account.opening_balance,
                'debit': debit,
                'credit': credit,
                'balance': balance
            })

        return render_template('accounts/trial_balance.html',
                               trial_balance=trial_balance_data,
                               total_debit=total_debit,
                               total_credit=total_credit,
                               as_of_date=as_of_date,
                               is_balanced=abs(total_debit - total_credit) < 0.01)

    @app.route('/accounts/income_statement')
    @login_required
    @role_required('admin', 'finance')
    def income_statement():
        """قائمة الدخل (الأرباح والخسائر)"""
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        today = datetime.now().date()

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = datetime(today.year, today.month, 1).date()
                end_date = today
        else:
            start_date = datetime(today.year, today.month, 1).date()
            end_date = today

        revenues = Account.query.filter_by(account_type='revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='expense', is_active=True).all()

        revenue_data = []
        expense_data = []
        total_revenue = 0
        total_expense = 0

        for acc in revenues:
            balance = acc.get_balance(end_date)
            revenue_data.append({'account': acc, 'balance': balance})
            total_revenue += balance

        for acc in expenses:
            balance = acc.get_balance(end_date)
            expense_data.append({'account': acc, 'balance': balance})
            total_expense += balance

        net_income = total_revenue - total_expense

        return render_template('accounts/income_statement.html',
                               revenue_data=revenue_data,
                               expense_data=expense_data,
                               total_revenue=total_revenue,
                               total_expense=total_expense,
                               net_income=net_income,
                               start_date=start_date,
                               end_date=end_date)

    @app.route('/accounts/balance_sheet')
    @login_required
    @role_required('admin', 'finance')
    def balance_sheet():
        """الميزانية العمومية - بدون بند الرواتب المصروفة"""
        from models import JournalEntry

        as_of_date = request.args.get('as_of_date')

        if not as_of_date:
            as_of_date = datetime.now().date()
        else:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

        # الحصول على الحسابات
        assets = Account.query.filter_by(account_type='asset', is_active=True).all()
        liabilities = Account.query.filter_by(account_type='liability', is_active=True).all()
        equity = Account.query.filter_by(account_type='equity', is_active=True).all()

        # حساب الأرصدة (بدون إضافة الرواتب المصروفة)
        asset_data = []
        liability_data = []
        equity_data = []

        total_assets = 0
        total_liabilities = 0
        total_equity = 0

        # الأصول
        for acc in assets:
            balance = acc.get_balance(as_of_date)
            asset_data.append({'account': acc, 'balance': balance})
            total_assets += balance

        # الخصوم (الحسابات الحقيقية فقط)
        for acc in liabilities:
            balance = acc.get_balance(as_of_date)
            # تخطي الحسابات الخاصة بالرواتب المصروفة إذا وجدت
            if 'الرواتب المصروفة' not in acc.name_ar:
                liability_data.append({'account': acc, 'balance': balance})
                total_liabilities += balance

        # حقوق الملكية
        for acc in equity:
            balance = acc.get_balance(as_of_date)
            equity_data.append({'account': acc, 'balance': balance})
            total_equity += balance

        # حساب الفرق والتوازن
        difference = total_assets - (total_liabilities + total_equity)
        is_balanced = abs(difference) < 0.01

        # التحقق من حالة إقفال المصروفات
        closing_entry = JournalEntry.query.filter_by(
            reference_type='closing_expenses'
        ).order_by(JournalEntry.entry_number.desc()).first()

        is_closed = False
        if closing_entry:
            # التحقق من عدم وجود قيد فتح
            reopen_entry = JournalEntry.query.filter_by(
                reference_type='reopen_period',
                reference_id=closing_entry.id
            ).first()
            is_closed = reopen_entry is None

        # حساب إجمالي المصروفات للعرض
        expense_accounts = Account.query.filter_by(account_type='expense', is_active=True).all()
        total_expenses = sum(e.get_balance(as_of_date) for e in expense_accounts)

        return render_template('accounts/balance_sheet.html',
                               asset_data=asset_data,
                               liability_data=liability_data,
                               equity_data=equity_data,
                               total_assets=total_assets,
                               total_liabilities=total_liabilities,
                               total_equity=total_equity,
                               as_of_date=as_of_date,
                               difference=difference,
                               is_balanced=is_balanced,
                               is_closed=is_closed,
                               total_expenses=total_expenses,
                               now=datetime.now())

    @app.route('/accounts/close-expenses', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def close_expenses_api():
        """API لإقفال حسابات المصروفات"""
        from utils import auto_close_expenses

        try:
            journal_entry = auto_close_expenses()

            if journal_entry:
                return jsonify({
                    'success': True,
                    'message': f'تم إنشاء قيد إقفال رقم {journal_entry.entry_number}',
                    'entry_number': journal_entry.entry_number
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'لا توجد مصروفات للإقفال'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/accounts/reopen-period', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def reopen_period_api():
        """إعادة فتح الفترة المحاسبية - عكس قيد إقفال المصروفات"""
        from utils import reverse_journal_entry
        from models import JournalEntry

        try:
            # البحث عن آخر قيد إقفال للمصروفات
            closing_entry = JournalEntry.query.filter_by(
                reference_type='closing_expenses'
            ).order_by(JournalEntry.entry_number.desc()).first()

            if not closing_entry:
                return jsonify({
                    'success': False,
                    'error': 'لا يوجد قيد إقفال لعكسه. المصروفات غير مقفلة.'
                }), 400

            # التحقق من عدم وجود قيد عكسي مسبق
            existing_reverse = JournalEntry.query.filter(
                JournalEntry.reference_type == 'reopen_period',
                JournalEntry.reference_id == closing_entry.id
            ).first()

            if existing_reverse:
                return jsonify({
                    'success': False,
                    'error': f'تم فتح الفترة مسبقاً بالقيد {existing_reverse.entry_number}'
                }), 400

            # عكس قيد الإقفال
            reverse_entry = reverse_journal_entry(closing_entry.id)

            # تحديث وصف القيد العكسي
            reverse_entry.description = f'إعادة فتح الفترة - عكس قيد إقفال المصروفات {closing_entry.entry_number}'
            reverse_entry.reference_type = 'reopen_period'
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'تم فتح الفترة بنجاح',
                'entry_number': reverse_entry.entry_number,
                'reversed_entry': closing_entry.entry_number
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/accounts/redistribute-expenses', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def redistribute_expenses_api():
        """API لإعادة توزيع المصروفات العامة إلى حساباتها الصحيحة"""
        from utils import redistribute_expenses

        try:
            result = redistribute_expenses()

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'entry_number': result.get('entry_number'),
                    'distributed': result.get('distributed'),
                    'remaining': result.get('remaining')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result['message']
                }), 400

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/accounts/expense-details', methods=['GET'])
    @login_required
    @role_required('admin', 'finance')
    def get_expense_details():
        """الحصول على تفاصيل المصروفات للتحقق"""
        expenses = Account.query.filter_by(account_type='expense', is_active=True).all()

        expense_data = []
        total = 0

        for exp in expenses:
            balance = exp.get_balance()
            if balance != 0:
                expense_data.append({
                    'code': exp.code,
                    'name': exp.name_ar,
                    'balance': balance
                })
                total += balance

        return jsonify({
            'success': True,
            'expenses': expense_data,
            'total': total,
            'count': len(expense_data)
        })

    @app.route('/accounts/check-closing-status', methods=['GET'])
    @login_required
    @role_required('admin', 'finance')
    def check_closing_status():
        """التحقق من حالة إقفال المصروفات"""
        from models import JournalEntry

        # البحث عن قيد إقفال
        closing_entry = JournalEntry.query.filter_by(
            reference_type='closing_expenses'
        ).order_by(JournalEntry.entry_number.desc()).first()

        # البحث عن قيد فتح
        reopen_entry = None
        if closing_entry:
            reopen_entry = JournalEntry.query.filter_by(
                reference_type='reopen_period',
                reference_id=closing_entry.id
            ).first()

        # حساب إجمالي المصروفات
        expenses = Account.query.filter_by(account_type='expense').all()
        total_expenses = sum(e.get_balance() for e in expenses)

        return jsonify({
            'is_closed': closing_entry is not None,
            'closing_entry': closing_entry.entry_number if closing_entry else None,
            'closing_date': closing_entry.date.strftime('%Y-%m-%d') if closing_entry else None,
            'is_reopened': reopen_entry is not None,
            'reopen_entry': reopen_entry.entry_number if reopen_entry else None,
            'total_expenses': total_expenses
        })

    # ==================== فواتير الموردين (من الشركات إلى طلعت هائل) ====================

    # ==================== إدارة الموردين والفواتير (موحدة) ====================

    def generate_supplier_invoice_number():
        """توليد رقم فاتورة مورد تلقائي"""
        from datetime import datetime

        # الحصول على آخر رقم فاتورة
        last_invoice = SupplierInvoice.query.order_by(SupplierInvoice.id.desc()).first()

        if last_invoice and last_invoice.invoice_number:
            # استخراج الرقم من التنسيق SI-YYYYMMDD-XXX
            try:
                parts = last_invoice.invoice_number.split('-')
                if len(parts) >= 3:
                    last_num = int(parts[2])
                    new_num = last_num + 1
                else:
                    new_num = 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        # تنسيق التاريخ
        today = datetime.now()
        date_str = today.strftime('%Y%m%d')

        # تنسيق الرقم: SI-YYYYMMDD-XXX
        invoice_number = f"SI-{date_str}-{str(new_num).zfill(3)}"

        return invoice_number

    @app.route('/suppliers')
    @login_required
    @role_required('admin', 'finance')
    def suppliers_list():
        """عرض قائمة الموردين"""
        suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
        return render_template('suppliers/suppliers.html', suppliers=suppliers, now=datetime.now())

    @app.route('/suppliers/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_supplier():
        """إضافة مورد جديد"""
        if request.method == 'POST':
            try:
                supplier = Supplier(
                    name=request.form.get('name'),
                    name_ar=request.form.get('name_ar'),
                    contact_person=request.form.get('contact_person'),
                    phone=request.form.get('phone'),
                    email=request.form.get('email'),
                    address=request.form.get('address'),
                    tax_number=request.form.get('tax_number'),
                    bank_name=request.form.get('bank_name'),
                    bank_account=request.form.get('bank_account'),
                    supplier_type=request.form.get('supplier_type', 'general'),
                    notes=request.form.get('notes')
                )
                db.session.add(supplier)
                db.session.commit()
                flash('✅ تم إضافة المورد بنجاح', 'success')
                return redirect(url_for('suppliers_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return render_template('suppliers/add_supplier.html', now=datetime.now())

    @app.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def edit_supplier(supplier_id):
        """تعديل بيانات مورد"""
        supplier = Supplier.query.get_or_404(supplier_id)

        if request.method == 'POST':
            try:
                supplier.name = request.form.get('name')
                supplier.name_ar = request.form.get('name_ar')
                supplier.contact_person = request.form.get('contact_person')
                supplier.phone = request.form.get('phone')
                supplier.email = request.form.get('email')
                supplier.address = request.form.get('address')
                supplier.tax_number = request.form.get('tax_number')
                supplier.bank_name = request.form.get('bank_name')
                supplier.bank_account = request.form.get('bank_account')
                supplier.supplier_type = request.form.get('supplier_type', 'general')
                supplier.notes = request.form.get('notes')
                db.session.commit()
                flash('✅ تم تحديث بيانات المورد بنجاح', 'success')
                return redirect(url_for('suppliers_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return render_template('suppliers/edit_supplier.html', supplier=supplier, now=datetime.now())

    @app.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_supplier(supplier_id):
        """حذف مورد"""
        supplier = Supplier.query.get_or_404(supplier_id)
        supplier.is_active = False
        db.session.commit()
        flash('✅ تم حذف المورد بنجاح', 'success')
        return redirect(url_for('suppliers_list'))

    @app.route('/supplier-invoices')
    @login_required
    @role_required('admin', 'finance')
    def supplier_invoices_list():
        """عرض فواتير الموردين (موحدة)"""
        invoices = SupplierInvoice.query.order_by(SupplierInvoice.invoice_date.desc()).all()

        stats = {
            'total': len(invoices),
            'total_amount': sum(i.amount for i in invoices),
            'paid_amount': sum(i.paid_amount for i in invoices),
            'pending_amount': sum(i.remaining_amount for i in invoices),
            'paid_count': len([i for i in invoices if i.status == 'paid']),
            'partial_count': len([i for i in invoices if i.status == 'partial']),
            'pending_count': len([i for i in invoices if i.status == 'pending'])
        }

        categories = ExpenseCategory.query.filter_by(is_active=True).all()

        return render_template('suppliers/invoices.html',
                               invoices=invoices,
                               stats=stats,
                               categories=categories,
                               now=datetime.now())

    @app.route('/supplier-invoices/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_supplier_invoice():
        """إضافة فاتورة مورد جديدة مع توليد رقم تلقائي"""

        if request.method == 'POST':
            try:
                # توليد رقم فاتورة إذا كان الحقل فارغاً
                invoice_number = request.form.get('invoice_number')
                if not invoice_number or invoice_number.strip() == '':
                    invoice_number = generate_supplier_invoice_number()

                invoice = SupplierInvoice(
                    invoice_number=invoice_number,
                    supplier_id=request.form.get('supplier_id'),
                    category_id=request.form.get('category_id'),
                    amount=float(request.form.get('amount')),
                    invoice_date=datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date(),
                    due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get(
                        'due_date') else None,
                    remaining_amount=float(request.form.get('amount')),
                    description=request.form.get('description'),
                    notes=request.form.get('notes'),
                    created_by=current_user.id
                )
                db.session.add(invoice)
                db.session.flush()

                # إنشاء قيد محاسبي
                try:
                    create_supplier_invoice_journal_entry(invoice)
                    invoice.is_posted_to_accounts = True
                except Exception as je:
                    db.session.rollback()
                    flash(f'تمت إضافة الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                    return redirect(url_for('supplier_invoices_list'))

                db.session.commit()
                flash(f'✅ تم إضافة فاتورة المورد بنجاح (رقم: {invoice_number})', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')
                return redirect(url_for('add_supplier_invoice'))

            return redirect(url_for('supplier_invoices_list'))

        # GET request
        suppliers = Supplier.query.filter_by(is_active=True).all()
        categories = ExpenseCategory.query.filter_by(is_active=True).all()

        # توليد رقم فاتورة مقترح للعرض
        suggested_number = generate_supplier_invoice_number()

        return render_template('suppliers/add_invoice.html',
                               suppliers=suppliers,
                               categories=categories,
                               suggested_number=suggested_number,
                               now=datetime.now())

    @app.route('/supplier-invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def edit_supplier_invoice(invoice_id):
        """تعديل فاتورة مورد"""
        invoice = SupplierInvoice.query.get_or_404(invoice_id)

        if request.method == 'POST':
            try:
                invoice.invoice_number = request.form.get('invoice_number')
                invoice.supplier_id = request.form.get('supplier_id')
                invoice.category_id = request.form.get('category_id')
                invoice.amount = float(request.form.get('amount'))
                invoice.invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
                invoice.due_date = datetime.strptime(request.form.get('due_date'),
                                                     '%Y-%m-%d').date() if request.form.get('due_date') else None
                invoice.description = request.form.get('description')
                invoice.notes = request.form.get('notes')

                # إعادة حساب المتبقي إذا تغير المبلغ
                invoice.remaining_amount = invoice.amount - invoice.paid_amount
                if invoice.remaining_amount <= 0:
                    invoice.status = 'paid'
                elif invoice.paid_amount > 0:
                    invoice.status = 'partial'
                else:
                    invoice.status = 'pending'

                db.session.commit()
                flash('✅ تم تحديث الفاتورة بنجاح', 'success')
                return redirect(url_for('supplier_invoices_list'))

            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        suppliers = Supplier.query.filter_by(is_active=True).all()
        categories = ExpenseCategory.query.filter_by(is_active=True).all()

        return render_template('suppliers/edit_invoice.html',
                               invoice=invoice,
                               suppliers=suppliers,
                               categories=categories,
                               now=datetime.now())

    @app.route('/supplier-invoices/delete/<int:invoice_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_supplier_invoice(invoice_id):
        """حذف فاتورة مورد"""
        invoice = SupplierInvoice.query.get_or_404(invoice_id)

        try:
            # حذف المدفوعات المرتبطة أولاً
            for payment in invoice.payments:
                db.session.delete(payment)
            db.session.delete(invoice)
            db.session.commit()
            flash('✅ تم حذف الفاتورة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

        return redirect(url_for('supplier_invoices_list'))

    @app.route('/supplier-invoices/pay/<int:invoice_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def pay_supplier_invoice(invoice_id):
        """تسديد فاتورة مورد - مع التحقق من الرصيد الموجب"""
        from models import Account

        invoice = SupplierInvoice.query.get_or_404(invoice_id)

        try:
            payment_amount = float(request.form.get('payment_amount', 0))
            payment_method = request.form.get('payment_method')
            reference_number = request.form.get('reference_number')

            if payment_amount <= 0:
                flash('⚠️ المبلغ يجب أن يكون أكبر من صفر', 'danger')
                return redirect(url_for('supplier_invoices_list'))

            if payment_amount > invoice.remaining_amount:
                flash('⚠️ المبلغ المدفوع يتجاوز المبلغ المتبقي', 'danger')
                return redirect(url_for('supplier_invoices_list'))

            # ========== التحقق من الرصيد الموجب ==========
            # تحديد حساب الدفع
            if payment_method == 'bank_transfer':
                payment_account = Account.query.filter_by(code='110002').first()
                account_name = "البنك"
            else:
                payment_account = Account.query.filter_by(code='110001').first()
                account_name = "الصندوق"

            if not payment_account:
                flash(f'⚠️ حساب {account_name} غير موجود في النظام', 'danger')
                return redirect(url_for('supplier_invoices_list'))

            # التحقق من الرصيد
            current_balance = payment_account.get_balance()
            if current_balance < payment_amount:
                flash(f'⚠️ رصيد {account_name} غير كافٍ!', 'danger')
                flash(f'📊 الرصيد المتوفر: {current_balance:,.2f} ريال', 'warning')
                flash(f'💰 المبلغ المطلوب: {payment_amount:,.2f} ريال', 'warning')
                return redirect(url_for('supplier_invoices_list'))
            # ============================================

            # تسجيل الدفع
            payment = SupplierInvoicePayment(
                invoice_id=invoice.id,
                amount=payment_amount,
                payment_date=datetime.now().date(),
                payment_method=payment_method,
                reference_number=reference_number,
                created_by=current_user.id
            )
            db.session.add(payment)

            # تحديث الفاتورة
            invoice.paid_amount += payment_amount
            invoice.remaining_amount -= payment_amount
            invoice.payment_method = payment_method
            invoice.reference_number = reference_number

            if invoice.remaining_amount <= 0:
                invoice.status = 'paid'
            else:
                invoice.status = 'partial'

            db.session.flush()

            # إنشاء قيد محاسبي للدفع
            try:
                create_supplier_invoice_payment_journal_entry(invoice, payment_amount, payment_method)
                payment.is_posted_to_accounts = True
            except Exception as je:
                db.session.rollback()
                flash(f'تم تسديد الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                return redirect(url_for('supplier_invoices_list'))

            db.session.commit()
            flash(f'✅ تم تسديد مبلغ {payment_amount:,.0f} ريال بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('supplier_invoices_list'))

    @app.route('/supplier-invoices/report')
    @login_required
    @role_required('admin', 'finance')
    def supplier_invoices_report():
        """تقرير فواتير الموردين"""
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category_id = request.args.get('category_id', type=int)
        supplier_id = request.args.get('supplier_id', type=int)

        query = SupplierInvoice.query

        if start_date:
            query = query.filter(SupplierInvoice.invoice_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(SupplierInvoice.invoice_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if category_id:
            query = query.filter(SupplierInvoice.category_id == category_id)
        if supplier_id:
            query = query.filter(SupplierInvoice.supplier_id == supplier_id)

        invoices = query.order_by(SupplierInvoice.invoice_date.desc()).all()
        suppliers = Supplier.query.filter_by(is_active=True).all()
        categories = ExpenseCategory.query.filter_by(is_active=True).all()

        # إحصائيات
        total_amount = sum(i.amount for i in invoices)
        total_paid = sum(i.paid_amount for i in invoices)
        total_remaining = sum(i.remaining_amount for i in invoices)

        # إحصائيات حسب الفئة
        category_stats = []
        for cat in categories:
            cat_invoices = [i for i in invoices if i.category_id == cat.id]
            if cat_invoices:
                category_stats.append({
                    'category': cat,
                    'count': len(cat_invoices),
                    'total': sum(i.amount for i in cat_invoices),
                    'paid': sum(i.paid_amount for i in cat_invoices)
                })

        return render_template('suppliers/invoices_report.html',
                               invoices=invoices,
                               suppliers=suppliers,
                               categories=categories,
                               category_stats=category_stats,
                               total_amount=total_amount,
                               total_paid=total_paid,
                               total_remaining=total_remaining,
                               start_date=start_date,
                               end_date=end_date,
                               selected_category=category_id,
                               selected_supplier=supplier_id,
                               now=datetime.now())

    @app.route('/expense-categories')
    @login_required
    @role_required('admin', 'finance')
    def expense_categories_list():
        """عرض فئات المصروفات"""
        categories = ExpenseCategory.query.filter_by(is_active=True).all()
        return render_template('suppliers/categories.html', categories=categories, now=datetime.now())

    @app.route('/expense-categories/add', methods=['POST'])
    @login_required
    @role_required('admin')
    def add_expense_category():
        """إضافة فئة مصروفات جديدة"""
        try:
            category = ExpenseCategory(
                name=request.form.get('name'),
                name_ar=request.form.get('name_ar'),
                account_code=request.form.get('account_code'),
                parent_id=request.form.get('parent_id') or None
            )
            db.session.add(category)
            db.session.commit()
            flash('✅ تم إضافة الفئة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('expense_categories_list'))

    @app.route('/expense-categories/edit/<int:category_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def edit_expense_category(category_id):
        """تعديل فئة مصروفات"""
        category = ExpenseCategory.query.get_or_404(category_id)

        if request.method == 'POST':
            try:
                category.name = request.form.get('name')
                category.name_ar = request.form.get('name_ar')
                category.account_code = request.form.get('account_code')
                category.parent_id = request.form.get('parent_id') or None
                db.session.commit()
                flash('✅ تم تحديث الفئة بنجاح', 'success')
                return redirect(url_for('expense_categories_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        # GET request - عرض نموذج التعديل
        categories = ExpenseCategory.query.filter(
            ExpenseCategory.is_active == True,
            ExpenseCategory.id != category_id
        ).all()
        accounts = Account.query.filter_by(account_type='expense', is_active=True).order_by(Account.code).all()

        return render_template('suppliers/edit_category.html',
                               category=category,
                               categories=categories,
                               accounts=accounts,
                               now=datetime.now())

    @app.route('/expense-categories/delete/<int:category_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_expense_category(category_id):
        """حذف فئة مصروفات (تعطيلها فقط)"""
        category = ExpenseCategory.query.get_or_404(category_id)
        category.is_active = False
        db.session.commit()
        flash('✅ تم حذف الفئة بنجاح', 'success')
        return redirect(url_for('expense_categories_list'))

    @app.route('/expense-categories/toggle/<int:category_id>', methods=['POST'])
    @login_required
    @role_required('admin')
    def toggle_expense_category(category_id):
        """تفعيل/تعطيل فئة مصروفات"""
        category = ExpenseCategory.query.get_or_404(category_id)
        category.is_active = not category.is_active
        db.session.commit()
        status = 'تفعيل' if category.is_active else 'تعطيل'
        flash(f'✅ تم {status} الفئة بنجاح', 'success')
        return redirect(url_for('expense_categories_list'))

    @app.route('/supplier-invoices/print/<int:invoice_id>')
    @login_required
    @role_required('admin', 'finance')
    def print_supplier_invoice(invoice_id):
        """طباعة فاتورة مورد"""
        invoice = SupplierInvoice.query.get_or_404(invoice_id)

        company_info = {
            'name': 'طلعت هائل للخدمات والاستشارات الزراعية',
            'name_en': 'TALAAT HAIL FOR AGRICULTURAL SERVICES AND CONSULTATIONS',
            'address': 'الجمهورية اليمنية - محافظة الحديدة',
            'phone': '+967 xxx xxx xxx',
            'email': 'info@talaathail.com',
            'tax_number': '123456789'
        }

        return render_template('suppliers/print_invoice.html',
                               invoice=invoice,
                               company_info=company_info,
                               now=datetime.now())

    @app.route('/invoices/reverse/<int:invoice_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def reverse_invoice(invoice_id):
        """عكس القيد المحاسبي للفاتورة وحذفها"""
        invoice = Invoice.query.get_or_404(invoice_id)

        if not invoice.has_journal_entry():
            flash('⚠️ هذه الفاتورة ليس لها قيد محاسبي لعكسه', 'danger')
            return redirect(url_for('invoices_list'))

        if invoice.is_paid:
            flash('⚠️ لا يمكن عكس قيد فاتورة مدفوعة', 'danger')
            return redirect(url_for('invoices_list'))

        try:
            # عكس القيد المحاسبي
            reverse_entry = reverse_invoice_journal_entry(invoice)

            # تحديث العقد المرتبط
            contract = Contract.query.get(invoice.contract_id)
            if contract:
                contract.amount_received -= invoice.amount
                contract.remaining_amount = contract.contract_value - contract.amount_received
                if contract.remaining_amount > 0:
                    contract.status = 'active'
                elif contract.remaining_amount == 0:
                    contract.status = 'completed'

            # حذف الفاتورة
            db.session.delete(invoice)
            db.session.commit()

            flash(f'✅ تم عكس القيد المحاسبي (رقم: {reverse_entry.entry_number}) وحذف الفاتورة بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

        return redirect(url_for('invoices_list'))


    @app.route('/financial/reverse_transaction/<int:trans_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def reverse_transaction(trans_id):
        """عكس القيد المحاسبي للمعاملة المالية وحذفها"""
        transaction = FinancialTransaction.query.get_or_404(trans_id)

        if not transaction.journal_entry_id:
            flash('⚠️ هذه المعاملة ليس لها قيد محاسبي لعكسه', 'danger')
            return redirect(url_for('transactions_list'))

        if transaction.is_settled:
            flash('⚠️ لا يمكن عكس قيد معاملة تم ترحيلها', 'danger')
            return redirect(url_for('transactions_list'))

        try:
            # عكس القيد المحاسبي
            reverse_entry = reverse_journal_entry(transaction.journal_entry_id)

            # حذف المعاملة
            db.session.delete(transaction)
            db.session.commit()

            flash(f'✅ تم عكس القيد المحاسبي (رقم: {reverse_entry.entry_number}) وحذف المعاملة بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

        return redirect(url_for('transactions_list'))

    @app.route('/financial/collect-customers', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def collect_customers():
        """تحصيل مستحقات العملاء"""
        from models import Account, JournalEntry, JournalEntryDetail
        from datetime import datetime
        from utils import get_next_entry_number

        try:
            amount = float(request.form.get('amount', 0))
            payment_method = request.form.get('payment_method', 'bank')

            if amount <= 0:
                flash('⚠️ المبلغ يجب أن يكون أكبر من صفر', 'danger')
                return redirect(url_for('chart_of_accounts'))

            customers = Account.query.filter_by(code='120001').first()
            current_balance = customers.get_balance()

            if amount > current_balance:
                flash(f'⚠️ المبلغ المطلوب ({amount:,.2f}) يتجاوز رصيد العملاء ({current_balance:,.2f})', 'danger')
                return redirect(url_for('chart_of_accounts'))

            if payment_method == 'bank':
                target_account = Account.query.filter_by(code='110002').first()
                method_name = 'البنك'
            else:
                target_account = Account.query.filter_by(code='110001').first()
                method_name = 'الصندوق'

            if not target_account:
                flash(f'⚠️ حساب {method_name} غير موجود', 'danger')
                return redirect(url_for('chart_of_accounts'))

            # إنشاء قيد التحصيل
            entry_number = get_next_entry_number()

            journal_entry = JournalEntry(
                entry_number=entry_number,
                date=datetime.now().date(),
                description=f'تحصيل مبلغ {amount:,.2f} ريال من العملاء عبر {method_name}',
                reference_type='collection',
                reference_id=None,
                created_by=current_user.id
            )
            db.session.add(journal_entry)
            db.session.flush()

            # مدين: البنك/الصندوق
            detail1 = JournalEntryDetail(
                entry_id=journal_entry.id,
                account_id=target_account.id,
                debit=amount,
                credit=0,
                description='تحصيل من العملاء'
            )
            db.session.add(detail1)

            # دائن: العملاء
            detail2 = JournalEntryDetail(
                entry_id=journal_entry.id,
                account_id=customers.id,
                debit=0,
                credit=amount,
                description='تخفيض رصيد العملاء'
            )
            db.session.add(detail2)

            db.session.commit()

            flash(f'✅ تم تحصيل {amount:,.2f} ريال من العملاء', 'success')
            flash(f'📋 رقم القيد: {entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('chart_of_accounts'))

    # ==================== دوال رواتب العمال والتكاليف الإضافية ====================

    def calculate_worker_monthly_cost(employee, attendance_days, month_year):
        """
        حساب التكلفة الشهرية الكاملة للعامل

        التوزيع:
        - الراتب الأساسي: 2000 ريال شهرياً (موزع حسب أيام العمل)
        - بدل سكن: 500 ريال لكل يوم عمل (للساكنين فقط)
        - التأمين: 10800 ريال شهرياً (ثابت)
        - بدل ملابس: 24480 ريال سنوياً ÷ 12 = 2040 ريال شهرياً
        - بطائق صحية: 15000 ريال سنوياً ÷ 12 = 1250 ريال شهرياً

        Returns:
            dict: تفاصيل التكلفة
        """
        # الراتب الأساسي حسب أيام العمل
        daily_rate = employee.basic_salary / 30  # 2000 / 30 = 66.67
        basic_salary = daily_rate * attendance_days

        # بدل السكن (للساكنين فقط) - 500 لكل يوم عمل
        resident_allowance = 0
        if employee.is_resident:
            resident_allowance = 500 * attendance_days

        # التأمين الشهري (ثابت)
        insurance = employee.monthly_insurance  # 10800

        # بدل الملابس الشهري (تقسيط سنوي)
        monthly_clothing = employee.clothing_allowance / 12  # 24480 / 12 = 2040

        # بدل البطائق الصحية الشهري (تقسيط سنوي)
        monthly_health = employee.health_card_allowance / 12  # 15000 / 12 = 1250

        # إجمالي التكلفة الشهرية
        total_cost = basic_salary + resident_allowance + insurance + monthly_clothing + monthly_health

        return {
            'employee_id': employee.id,
            'employee_name': employee.name,
            'month_year': month_year,
            'attendance_days': attendance_days,
            'basic_salary': round(basic_salary, 2),
            'resident_allowance': round(resident_allowance, 2),
            'insurance': round(insurance, 2),
            'clothing_allowance': round(monthly_clothing, 2),
            'health_card_allowance': round(monthly_health, 2),
            'total_cost': round(total_cost, 2),
            'breakdown': {
                'basic_salary_formula': f'{employee.basic_salary} / 30 * {attendance_days} = {basic_salary:.2f}',
                'resident_formula': f'500 * {attendance_days} = {resident_allowance:.2f}' if employee.is_resident else 'غير ساكن',
                'insurance_formula': f'10800 شهرياً = {insurance:.2f}',
                'clothing_formula': f'24480 / 12 = {monthly_clothing:.2f}',
                'health_formula': f'15000 / 12 = {monthly_health:.2f}'
            }
        }

    def calculate_all_workers_monthly_cost(company_id, attendance_data, month_year=None):
        """
        حساب تكاليف جميع عمال الشركة في شهر معين

        Args:
            company_id: معرف الشركة
            attendance_data: dict {employee_id: attendance_days}
            month_year: الشهر والسنة (MM-YYYY)

        Returns:
            dict: إجمالي التكاليف
        """
        from datetime import datetime
        from models import Employee

        if month_year is None:
            month_year = datetime.now().strftime('%m-%Y')

        employees = Employee.query.filter_by(
            company_id=company_id,
            employee_type='worker',
            is_active=True
        ).all()

        results = []
        total_basic = 0
        total_resident = 0
        total_insurance = 0
        total_clothing = 0
        total_health = 0
        total_all = 0

        for employee in employees:
            attendance_days = attendance_data.get(employee.id, 0)

            # حساب التكلفة
            cost = calculate_worker_monthly_cost(employee, attendance_days, month_year)

            results.append(cost)

            # تجميع الإجماليات
            total_basic += cost['basic_salary']
            total_resident += cost['resident_allowance']
            total_insurance += cost['insurance']
            total_clothing += cost['clothing_allowance']
            total_health += cost['health_card_allowance']
            total_all += cost['total_cost']

        return {
            'success': True,
            'month_year': month_year,
            'company_id': company_id,
            'employees_count': len(results),
            'summary': {
                'total_basic_salaries': round(total_basic, 2),
                'total_resident_allowances': round(total_resident, 2),
                'total_insurance': round(total_insurance, 2),
                'total_clothing_allowance': round(total_clothing, 2),
                'total_health_cards': round(total_health, 2),
                'grand_total': round(total_all, 2)
            },
            'details': results
        }

    def create_worker_salary_journal_entry(company_id, month_year, cost_summary):
        """
        إنشاء قيد محاسبي لرواتب وتكاليف العمال

        القيد يتكون من:
        مدين:
            - مصروف رواتب العمال الأساسية (511001)
            - مصروف بدل سكن العمال (511002)
            - مصروف تأمين العمال (511003)
            - مصروف بدل ملابس العمال (511004)
            - مصروف بطائق صحية للعمال (511005)

        دائن:
            - رواتب العمال المستحقة (211001)
            - بدلات العمال المستحقة (211002)
            - تأمينات مستحقة (211003)
        """
        from models import Account, JournalEntry, JournalEntryDetail, db
        from datetime import datetime
        from utils import get_next_entry_number

        summary = cost_summary['summary']

        # البحث عن الحسابات
        basic_salary_expense = Account.query.filter_by(code='511001').first()
        resident_allowance_expense = Account.query.filter_by(code='511002').first()
        insurance_expense = Account.query.filter_by(code='511003').first()
        clothing_expense = Account.query.filter_by(code='511004').first()
        health_expense = Account.query.filter_by(code='511005').first()

        salaries_payable = Account.query.filter_by(code='211001').first()
        allowances_payable = Account.query.filter_by(code='211002').first()
        insurance_payable = Account.query.filter_by(code='211003').first()

        # التأكد من وجود الحسابات - إنشاؤها إذا لم تكن موجودة
        from models import create_labor_accounts
        if not all([basic_salary_expense, resident_allowance_expense, insurance_expense,
                    clothing_expense, health_expense, salaries_payable, allowances_payable, insurance_payable]):
            create_labor_accounts()
            # إعادة المحاولة
            basic_salary_expense = Account.query.filter_by(code='511001').first()
            resident_allowance_expense = Account.query.filter_by(code='511002').first()
            insurance_expense = Account.query.filter_by(code='511003').first()
            clothing_expense = Account.query.filter_by(code='511004').first()
            health_expense = Account.query.filter_by(code='511005').first()
            salaries_payable = Account.query.filter_by(code='211001').first()
            allowances_payable = Account.query.filter_by(code='211002').first()
            insurance_payable = Account.query.filter_by(code='211003').first()

        entry_number = get_next_entry_number()

        # إنشاء القيد المحاسبي
        journal_entry = JournalEntry(
            entry_number=entry_number,
            date=datetime.now().date(),
            description=f'رواتب وتكاليف العمال عن شهر {month_year} - شركة رقم {company_id}',
            reference_type='worker_salaries',
            reference_id=None,
            created_by=current_user.id
        )
        db.session.add(journal_entry)
        db.session.flush()

        # إضافة تفاصيل القيد (مدين)
        debit_entries = [
            (basic_salary_expense.id, summary['total_basic_salaries'], 'رواتب العمال الأساسية'),
            (resident_allowance_expense.id, summary['total_resident_allowances'], 'بدل سكن العمال'),
            (insurance_expense.id, summary['total_insurance'], 'تأمين العمال'),
            (clothing_expense.id, summary['total_clothing_allowance'], 'بدل ملابس العمال'),
            (health_expense.id, summary['total_health_cards'], 'بطائق صحية للعمال')
        ]

        for acc_id, amount, desc in debit_entries:
            if amount > 0:
                detail = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=acc_id,
                    debit=amount,
                    credit=0,
                    description=desc
                )
                db.session.add(detail)

        # إضافة تفاصيل القيد (دائن)
        total_salaries = summary['total_basic_salaries'] + summary['total_resident_allowances']
        total_allowances = summary['total_clothing_allowance'] + summary['total_health_cards']

        credit_entries = [
            (salaries_payable.id, total_salaries, 'رواتب العمال المستحقة'),
            (allowances_payable.id, total_allowances, 'بدلات العمال المستحقة'),
            (insurance_payable.id, summary['total_insurance'], 'تأمينات مستحقة')
        ]

        for acc_id, amount, desc in credit_entries:
            if amount > 0:
                detail = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=acc_id,
                    debit=0,
                    credit=amount,
                    description=desc
                )
                db.session.add(detail)

        db.session.commit()

        return journal_entry

    @app.route('/labor/costs/calculate', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def calculate_labor_costs():
        """حساب تكاليف العمال الشهرية"""
        from models import AttendancePeriodTransfer
        import json

        try:
            transfer_id = request.form.get('transfer_id')
            month_year = request.form.get('month_year')

            if not transfer_id:
                flash('⚠️ الرجاء اختيار فترة ترحيل أولاً', 'danger')
                return redirect(url_for('period_transfer_list'))

            transfer = AttendancePeriodTransfer.query.get(transfer_id)
            if not transfer:
                flash('⚠️ فترة الترحيل غير موجودة', 'danger')
                return redirect(url_for('period_transfer_list'))

            # تجميع بيانات الحضور من تفاصيل الترحيل
            attendance_data = {}
            for detail in transfer.transfers_details:
                if detail.employee and detail.employee.employee_type == 'worker':
                    attendance_data[detail.employee_id] = detail.attendance_days

            if not attendance_data:
                flash('⚠️ لا يوجد عمال في فترة الترحيل هذه', 'warning')
                return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

            # حساب التكاليف
            result = calculate_all_workers_monthly_cost(
                company_id=transfer.company_id,
                attendance_data=attendance_data,
                month_year=month_year or transfer.period_name
            )

            # تخزين النتيجة في session لعرضها
            session['labor_cost_result'] = result

            flash(f'✅ تم حساب تكاليف {result["employees_count"]} عامل بنجاح', 'success')
            flash(f'💰 إجمالي التكاليف: {result["summary"]["grand_total"]:,.2f} ريال', 'info')

            return render_template('labor/costs_report.html',
                                   result=result,
                                   transfer=transfer,
                                   now=datetime.now())

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('period_transfer_list'))

    @app.route('/labor/costs/journal/<int:transfer_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def create_labor_costs_journal(transfer_id):
        """إنشاء قيد محاسبي لتكاليف العمال"""
        import json

        try:
            transfer = AttendancePeriodTransfer.query.get(transfer_id)
            if not transfer:
                flash('⚠️ فترة الترحيل غير موجودة', 'danger')
                return redirect(url_for('period_transfer_list'))

            # استعادة النتيجة من session أو إعادة حسابها
            result = session.get('labor_cost_result')
            if not result or result.get('company_id') != transfer.company_id:
                # إعادة الحساب إذا لم تكن النتيجة موجودة
                attendance_data = {}
                for detail in transfer.transfers_details:
                    if detail.employee and detail.employee.employee_type == 'worker':
                        attendance_data[detail.employee_id] = detail.attendance_days

                result = calculate_all_workers_monthly_cost(
                    company_id=transfer.company_id,
                    attendance_data=attendance_data,
                    month_year=transfer.period_name
                )

            # التحقق من وجود قيد مسبق
            existing = JournalEntry.query.filter(
                JournalEntry.reference_type == 'worker_salaries',
                JournalEntry.description.like(f'%{transfer.period_name}%')
            ).first()

            if existing:
                flash(f'⚠️ يوجد قيد محاسبي مسبق لهذه الفترة: {existing.entry_number}', 'warning')
                return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

            # إنشاء القيد المحاسبي
            journal_entry = create_worker_salary_journal_entry(
                company_id=transfer.company_id,
                month_year=transfer.period_name,
                cost_summary=result
            )

            flash(f'✅ تم إنشاء القيد المحاسبي لتكاليف العمال', 'success')
            flash(f'📋 رقم القيد: {journal_entry.entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

    @app.route('/labor/costs/report')
    @login_required
    @role_required('admin', 'finance')
    def labor_costs_report():
        """تقرير تكاليف العمال"""
        company_id = request.args.get('company_id', type=int)
        month_year = request.args.get('month_year')

        from datetime import datetime
        if not month_year:
            month_year = datetime.now().strftime('%m-%Y')

        from models import LaborMonthlyCost

        query = LaborMonthlyCost.query

        if company_id:
            query = query.join(Employee).filter(Employee.company_id == company_id)

        if month_year:
            query = query.filter(LaborMonthlyCost.month_year == month_year)

        costs = query.all()

        # تجميع الإحصائيات
        summary = {
            'total_basic_salaries': sum(c.basic_salary_cost for c in costs),
            'total_resident_allowances': sum(c.resident_allowance_cost for c in costs),
            'total_insurance': sum(c.insurance_cost for c in costs),
            'total_clothing_allowance': sum(c.clothing_allowance_cost for c in costs),
            'total_health_cards': sum(c.health_card_cost for c in costs),
            'grand_total': sum(c.total_cost for c in costs)
        }

        companies = Company.query.all()

        return render_template('labor/costs_report.html',
                               costs=costs,
                               summary=summary,
                               companies=companies,
                               selected_company=company_id,
                               selected_month=month_year,
                               now=datetime.now())

    @app.route('/labor/contractor/annual')
    @login_required
    @role_required('admin', 'finance')
    def contractor_annual_costs():
        """عرض تكاليف المتعهد السنوية (ضريبة وزكاة)"""
        from models import ContractorAnnualCost

        year = request.args.get('year', type=int)
        if not year:
            year = datetime.now().year

        costs = ContractorAnnualCost.query.filter_by(year=year).all()

        # حساب الإجماليات
        total_tax = sum(c.tax_amount for c in costs)
        total_zakat = sum(c.zakat_amount for c in costs)

        return render_template('labor/contractor_costs.html',
                               costs=costs,
                               year=year,
                               total_tax=total_tax,
                               total_zakat=total_zakat,
                               now=datetime.now())

    @app.route('/labor/contractor/journal/<int:year>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def create_contractor_journal(year):
        """إنشاء قيد محاسبي لضريبة وزكاة المتعهد"""
        from models import Account, JournalEntry, JournalEntryDetail, ContractorAnnualCost, db
        from utils import get_next_entry_number
        from datetime import datetime

        try:
            company_id = request.form.get('company_id', type=int)

            # البحث أو إنشاء سجل التكلفة السنوية
            annual_cost = ContractorAnnualCost.query.filter_by(
                year=year,
                company_id=company_id
            ).first()

            if not annual_cost:
                annual_cost = ContractorAnnualCost(
                    year=year,
                    company_id=company_id,
                    tax_amount=500000,
                    zakat_amount=75000
                )
                db.session.add(annual_cost)
                db.session.commit()

            # التحقق من وجود قيد مسبق
            existing = JournalEntry.query.filter(
                JournalEntry.reference_type == 'contractor_annual',
                JournalEntry.reference_id == annual_cost.id
            ).first()

            if existing:
                flash(f'⚠️ يوجد قيد محاسبي مسبق لهذه السنة: {existing.entry_number}', 'warning')
                return redirect(url_for('contractor_annual_costs', year=year))

            # البحث عن الحسابات
            tax_expense = Account.query.filter_by(code='521001').first()
            zakat_expense = Account.query.filter_by(code='521002').first()
            tax_payable = Account.query.filter_by(code='221001').first()
            zakat_payable = Account.query.filter_by(code='221002').first()

            # إنشاء الحسابات إذا لم تكن موجودة
            from models import create_labor_accounts
            if not all([tax_expense, zakat_expense, tax_payable, zakat_payable]):
                create_labor_accounts()
                tax_expense = Account.query.filter_by(code='521001').first()
                zakat_expense = Account.query.filter_by(code='521002').first()
                tax_payable = Account.query.filter_by(code='221001').first()
                zakat_payable = Account.query.filter_by(code='221002').first()

            entry_number = get_next_entry_number()

            # إنشاء القيد المحاسبي
            journal_entry = JournalEntry(
                entry_number=entry_number,
                date=datetime.now().date(),
                description=f'إقفال ضريبة وزكاة المتعهد عن سنة {year}',
                reference_type='contractor_annual',
                reference_id=annual_cost.id,
                created_by=current_user.id
            )
            db.session.add(journal_entry)
            db.session.flush()

            # مدين: مصروفات الضريبة والزكاة
            if annual_cost.tax_amount > 0:
                detail1 = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=tax_expense.id,
                    debit=annual_cost.tax_amount,
                    credit=0,
                    description=f'ضريبة المتعهدين عن سنة {year}'
                )
                db.session.add(detail1)

            if annual_cost.zakat_amount > 0:
                detail2 = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=zakat_expense.id,
                    debit=annual_cost.zakat_amount,
                    credit=0,
                    description=f'زكاة المتعهدين عن سنة {year}'
                )
                db.session.add(detail2)

            # دائن: التزامات تجاه الجهات
            if annual_cost.tax_amount > 0:
                detail3 = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=tax_payable.id,
                    debit=0,
                    credit=annual_cost.tax_amount,
                    description=f'ضريبة مستحقة للجهات الضريبية'
                )
                db.session.add(detail3)

            if annual_cost.zakat_amount > 0:
                detail4 = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=zakat_payable.id,
                    debit=0,
                    credit=annual_cost.zakat_amount,
                    description=f'زكاة مستحقة'
                )
                db.session.add(detail4)

            # تحديث حالة الترحيل
            annual_cost.is_paid = True
            annual_cost.paid_date = datetime.now().date()
            annual_cost.payment_reference = entry_number

            db.session.commit()

            flash(f'✅ تم إنشاء القيد المحاسبي لضريبة وزكاة سنة {year}', 'success')
            flash(f'📋 رقم القيد: {entry_number}', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('contractor_annual_costs', year=year))

    @app.route('/labor/costs/view/<int:transfer_id>')
    @login_required
    @role_required('admin', 'finance')
    def view_labor_costs(transfer_id):
        """عرض تفاصيل تكاليف العمال لفترة ترحيل"""
        from models import AttendancePeriodTransfer

        transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

        # حساب تكاليف العمال
        attendance_data = {}
        for detail in transfer.transfers_details:
            if detail.employee and detail.employee.employee_type == 'worker':
                attendance_data[detail.employee_id] = detail.attendance_days

        if not attendance_data:
            flash('⚠️ لا يوجد عمال في فترة الترحيل هذه', 'warning')
            return redirect(url_for('period_transfer_list'))

        result = calculate_all_workers_monthly_cost(
            company_id=transfer.company_id,
            attendance_data=attendance_data,
            month_year=transfer.period_name
        )

        return render_template('labor/costs_report.html',
                               result=result,
                               transfer=transfer,
                               now=datetime.now())





