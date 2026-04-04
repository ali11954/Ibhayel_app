# routes.py
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd

from models import db, User, Employee, Attendance, FinancialTransaction, Salary
from models import Evaluation, Company, Contract, Invoice,Location,Region,EvaluationCriteria,Expense
from utils import role_required, get_financial_month_dates, format_currency, get_regions
from config import Config
from flask import render_template, request, redirect, url_for, flash, jsonify

from sqlalchemy import func

def register_routes(app):
    # ==================== الصفحة الرئيسية ====================
    # ==================== الصفحة الرئيسية ====================
    @app.route('/')
    def index():
        # إذا لم يكن المستخدم مسجل دخول، قم بتوجيهه إلى صفحة تسجيل الدخول
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        # باقي الكود للمستخدمين المسجلين فقط
        try:
            today = datetime.now().date()

            # إحصائيات
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

            # آخر 5 حضور
            recent_attendance = Attendance.query.filter(
                Attendance.attendance_status == 'present'
            ).order_by(Attendance.date.desc()).limit(5).all()

            # توزيع الموظفين حسب المنطقة
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

            # بيانات الرواتب لآخر 6 أشهر
            salaries_data = []
            for i in range(5, -1, -1):
                date = datetime.now() - timedelta(days=30 * i)
                month_year = date.strftime('%m-%Y')
                month_name = date.strftime('%b %Y')

                total = db.session.query(db.func.sum(Salary.total_salary)).filter_by(month_year=month_year).scalar()
                total = float(total) if total else 0

                salaries_data.append({
                    'month': month_name,
                    'total': total
                })

            # حساب إجمالي الرواتب للشهر الحالي
            current_month = datetime.now().strftime('%m-%Y')
            salaries_total = db.session.query(db.func.sum(Salary.total_salary)).filter_by(
                month_year=current_month).scalar() or 0

            return render_template('index.html',
                                   stats=stats,
                                   recent_attendance=recent_attendance,
                                   regions_data=regions_data,
                                   salaries_data=salaries_data,
                                   now=datetime.now(),
                                   salaries_total=salaries_total)
        except Exception as e:
            print(f"Error in index: {e}")
            import traceback
            traceback.print_exc()
            return render_template('index.html',
                                   stats={'total_employees': 0, 'today_attendance': 0, 'pending_transactions': 0,
                                          'pending_salaries': 0},
                                   recent_attendance=[],
                                   regions_data=[],
                                   salaries_data=[],
                                   now=datetime.now(),
                                   salaries_total=0)
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
    @app.route('/employees')
    @login_required
    def employees_list():
        from sqlalchemy.orm import joinedload

        # تحميل الموظفين مع المشرفين والشركات
        employees = Employee.query.options(
            joinedload(Employee.employee_company),
            joinedload(Employee.supervisor)
        ).filter_by(is_active=True).all()

        regions = get_regions()
        companies = Company.query.all()
        return render_template('employees/employees.html',
                               employees=employees,
                               regions=regions,
                               companies=companies)

    @app.route('/employees/import', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def import_employees():
        if request.method == 'POST':
            file = request.files.get('file')
            if file and file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
                count = 0
                for _, row in df.iterrows():
                    if pd.notna(row.get('الاســــــم')) and pd.notna(row.get('رقم البطاقة')):
                        # البحث عن الشركة حسب الاسم إذا وجد
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

        companies = Company.query.all()  # جلب الشركات للقالب
        return render_template('employees/import_employees.html', companies=companies)

    @app.route('/employees/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def add_employee():
        if request.method == 'POST':
            card_number = request.form.get('card_number')
            code = request.form.get('code')
            employee_type = request.form.get('employee_type')
            supervisor_id = request.form.get('supervisor_id')

            # التحقق من رقم البطاقة والكود
            if Employee.query.filter_by(card_number=card_number).first():
                flash('رقم البطاقة موجود مسبقاً', 'danger')
            elif Employee.query.filter_by(code=code).first():
                flash('كود التعريف موجود مسبقاً', 'danger')
            else:
                # إنشاء الموظف
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

                # إنشاء حساب مستخدم إذا كان مشرف أو إداري
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

        # ========== GET Request ==========
        # جلب الشركات
        companies = Company.query.all()
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]

        # جلب المشرفين والإداريين (حسب job_title)
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

        # طباعة للتصحيح
        print("=" * 50)
        print("Companies Data:")
        for c in companies_data:
            print(f"  ID: {c['id']}, Name: {c['name']}")
        print("Supervisors Data (based on job_title):")
        for s in supervisors_data:
            print(f"  ID: {s['id']}, Name: {s['name']}, Job: {s['job_title']}, Company: {s['company_id']}")
        print("=" * 50)

        return render_template('employees/add_employee.html',
                               companies=companies_data,
                               supervisors=supervisors_data)

    @app.route('/api/areas/<int:company_id>')
    def get_areas_by_company(company_id):
        areas = Region.query.filter_by(company_id=company_id).all()
        return jsonify({'success': True, 'data': [{'id': a.id, 'name': a.name} for a in areas]})

    @app.route('/api/locations/<int:area_id>')
    def get_locations_by_area(area_id):
        locations = Location.query.filter_by(region_id=area_id).all()
        return jsonify({'success': True, 'data': [{'id': l.id, 'name': l.name} for l in locations]})

    @app.route('/employees/edit/<int:emp_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def edit_employee(emp_id):
        employee = Employee.query.get_or_404(emp_id)

        # تخزين القيم القديمة للمقارنة
        old_employee_type = employee.employee_type
        old_supervisor_id = employee.supervisor_id

        if request.method == 'POST':
            # التحقق من عدم وجود نفس الرقم أو الكود (باستثناء الموظف الحالي)
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

            # تحديث بيانات الموظف الأساسية
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

            # تحديث المشرف المسؤول للعامل
            if employee_type == 'worker' and supervisor_id:
                employee.supervisor_id = supervisor_id
            elif employee_type != 'worker':
                employee.supervisor_id = None

            # إذا تغير نوع الموظف من مشرف/إداري إلى عامل
            if old_employee_type in ['supervisor', 'admin'] and employee_type == 'worker':
                # حذف حساب المستخدم المرتبط
                if employee.user_id:
                    user = User.query.get(employee.user_id)
                    if user:
                        db.session.delete(user)
                    employee.user_id = None

            # إذا تغير نوع الموظف من عامل إلى مشرف/إداري
            elif old_employee_type == 'worker' and employee_type in ['supervisor', 'admin']:
                username = request.form.get('username')
                password = request.form.get('password')

                if username and password:
                    # التحقق من عدم وجود اسم مستخدم مكرر
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

            # إذا بقي مشرف/إداري وتم تغيير اسم المستخدم أو كلمة المرور
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

        # ========== GET Request ==========
        companies = Company.query.all()
        companies_data = [{'id': c.id, 'name': c.name} for c in companies]

        # جلب المشرفين والإداريين للتعديل (باستثناء الموظف الحالي)
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

        # إذا كان الموظف الحالي مشرف/إداري، جلب بيانات المستخدم
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
    @role_required('admin')
    def delete_employee(emp_id):
        employee = Employee.query.get_or_404(emp_id)
        employee.is_active = False
        db.session.commit()
        flash('تم حذف الموظف بنجاح', 'success')
        return redirect(url_for('employees_list'))

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

        # حساب التواريخ السابقة واللاحقة
        prev_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)

        # جلب بيانات الحضور
        attendances = Attendance.query.filter_by(date=selected_date).all()
        attendance_dict = {a.employee_id: a for a in attendances}

        # جلب الموظفين النشطين
        employees = Employee.query.filter_by(is_active=True).all()

        # جلب المناطق والشركات للفلترة
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

        return render_template('attendance/edit_attendance.html', attendance=attendance)

    @app.route('/attendance/bulk_save', methods=['POST'])
    @login_required
    def save_bulk_attendance():
        """حفظ جميع حالات الحضور دفعة واحدة"""
        try:
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            employee_ids = request.form.getlist('employee_ids')

            count = 0
            for emp_id in employee_ids:
                status = request.form.get(f'status_{emp_id}')

                if not status:
                    continue

                # التحقق من وجود تسجيل سابق
                existing = Attendance.query.filter_by(employee_id=emp_id, date=date).first()

                if status == 'absent':
                    # إذا كان غائب، احذف أي تسجيل موجود
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

                if existing:
                    # تحديث التسجيل الموجود
                    existing.attendance_status = status
                    existing.late_minutes = late_minutes
                    existing.sick_leave = status == 'sick'
                    existing.sick_leave_days = sick_leave_days
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
                        check_in_time=check_in_time,
                        check_out_time=check_out_time,
                        notes=request.form.get(f'notes_{emp_id}', ''),
                        created_by=current_user.id
                    )
                    db.session.add(attendance)

                count += 1

            db.session.commit()
            flash(f'تم تسجيل/تحديث حضور {count} موظف بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            print(f"Error in save_bulk_attendance: {e}")

        return redirect(url_for('attendance_list', date=date))
    # ==================== المعاملات المالية ====================
    @app.route('/financial/transactions')
    @login_required
    def transactions_list():
        transaction_type = request.args.get('type', 'all')
        employee_id = request.args.get('employee_id', type=int)

        query = FinancialTransaction.query
        if transaction_type != 'all':
            query = query.filter_by(transaction_type=transaction_type)
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
    def add_transaction():
        if request.method == 'POST':
            transaction = FinancialTransaction(
                employee_id=request.form.get('employee_id'),
                transaction_type=request.form.get('transaction_type'),
                amount=float(request.form.get('amount')),
                description=request.form.get('description'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                created_by=current_user.id
            )
            db.session.add(transaction)
            db.session.commit()
            flash('تم إضافة المعاملة المالية بنجاح', 'success')
            return redirect(url_for('transactions_list'))

        employees = Employee.query.filter_by(is_active=True).all()
        return render_template('financial/add_transaction.html',
                               employees=employees,
                               transaction_types=FinancialTransaction.TRANSACTION_TYPES)

    @app.route('/financial/delete_transaction/<int:trans_id>')
    @login_required
    @role_required('admin', 'finance')
    def delete_transaction(trans_id):
        transaction = FinancialTransaction.query.get_or_404(trans_id)
        db.session.delete(transaction)
        db.session.commit()
        flash('تم حذف المعاملة بنجاح', 'success')
        return redirect(url_for('transactions_list'))

    @app.route('/financial/transfer_to_salary', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def transfer_transaction_to_salary():
        """ترحيل معاملة واحدة إلى الراتب"""
        try:
            data = request.get_json()
            transaction_id = data.get('transaction_id')

            transaction = FinancialTransaction.query.get(transaction_id)
            if not transaction:
                return jsonify({'success': False, 'error': 'المعاملة غير موجودة'})

            if transaction.is_settled:
                return jsonify({'success': False, 'error': 'المعاملة تم ترحيلها مسبقاً'})

            # ترحيل المعاملة
            transaction.is_settled = True
            transaction.settled_date = datetime.now().date()

            db.session.commit()

            return jsonify({'success': True, 'message': 'تم ترحيل المعاملة بنجاح'})

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
    def financial_dashboard():
        """لوحة المالية الرئيسية"""
        from sqlalchemy import func

        # إحصائيات
        total_advances = FinancialTransaction.query.filter_by(transaction_type='advance', is_settled=False).count()
        total_overtime = FinancialTransaction.query.filter_by(transaction_type='overtime', is_settled=False).count()
        total_deductions = FinancialTransaction.query.filter_by(transaction_type='deduction', is_settled=False).count()
        total_salaries = Salary.query.filter_by(is_paid=False).count()

        # آخر المعاملات
        recent_transactions = FinancialTransaction.query.order_by(FinancialTransaction.date.desc()).limit(10).all()

        # آخر الرواتب
        recent_salaries = Salary.query.order_by(Salary.month_year.desc()).limit(10).all()

        return render_template('financial/dashboard.html',
                               total_advances=total_advances,
                               total_overtime=total_overtime,
                               total_deductions=total_deductions,
                               total_salaries=total_salaries,
                               recent_transactions=recent_transactions,
                               recent_salaries=recent_salaries)

    # ==================== Company Management Routes ====================
    @app.route('/companies')
    @login_required
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

    @app.route('/reports/dashboard')
    @login_required
    def reports_dashboard():
        """لوحة التقارير الرئيسية"""
        from sqlalchemy import func

        total_employees = Employee.query.filter_by(is_active=True).count()
        total_companies = Company.query.count()

        # رواتب الشهر الحالي
        current_month = datetime.now().strftime('%m-%Y')
        total_salaries_month = db.session.query(func.sum(Salary.total_salary)).filter_by(
            month_year=current_month).scalar() or 0

        # نسبة الحضور اليومية
        today = datetime.now().date()
        today_attendance = Attendance.query.filter_by(date=today, attendance_status='present').count()
        attendance_rate = round((today_attendance / total_employees * 100) if total_employees > 0 else 0)

        return render_template('reports/dashboard.html',
                               total_employees=total_employees,
                               total_companies=total_companies,
                               total_salaries_month=total_salaries_month,
                               attendance_rate=attendance_rate)
    # ==================== الرواتب ====================
    # ==================== الرواتب ====================
    @app.route('/financial/salaries')
    @login_required
    def salaries_list():
        """عرض الرواتب مع دعم فلترة التاريخ"""
        # الحصول على معاملات الفلترة
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        selected_month = request.args.get('month')

        # بناء الاستعلام الأساسي
        query = Salary.query

        # تطبيق فلتر التاريخ إذا وجد
        if start_date and end_date:
            # تحويل التواريخ إلى صيغة شهرية للمقارنة
            start_parts = start_date.split('-')
            end_parts = end_date.split('-')

            if len(start_parts) >= 2 and len(end_parts) >= 2:
                start_month = f"{start_parts[0]}-{start_parts[1]}"
                end_month = f"{end_parts[0]}-{end_parts[1]}"

                # فلترة الرواتب حسب نطاق الأشهر
                query = query.filter(
                    Salary.month_year >= start_month,
                    Salary.month_year <= end_month
                )

        # تطبيق فلتر الشهر إذا وجد
        if selected_month:
            query = query.filter_by(month_year=selected_month)

        # جلب جميع الرواتب مرتبة
        all_salaries = query.order_by(Salary.month_year.desc()).all()

        # الحصول على قائمة الأشهر المتاحة من جميع الرواتب (للقائمة المنسدلة)
        all_salaries_for_months = Salary.query.order_by(Salary.month_year.desc()).all()
        available_months = list(set([s.month_year for s in all_salaries_for_months]))
        available_months.sort(reverse=True)

        # إذا لم يتم تحديد شهر، استخدم أحدث شهر متاح
        if not selected_month and available_months and not (start_date or end_date):
            selected_month = available_months[0]
            all_salaries = Salary.query.filter_by(month_year=selected_month).order_by(Salary.month_year.desc()).all()

        return render_template('financial/salaries.html',
                               salaries=all_salaries,
                               available_months=available_months,
                               selected_month=selected_month or 'لا يوجد',
                               start_date=start_date,
                               end_date=end_date)
    @app.route('/financial/salary_calculation', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def salary_calculation():
        if request.method == 'POST':
            month_year = request.form.get('month_year')
            start_date, end_date = get_financial_month_dates(month_year)

            employees = Employee.query.filter_by(is_active=True).all()
            count = 0

            for employee in employees:
                existing = Salary.query.filter_by(employee_id=employee.id, month_year=month_year).first()
                if existing:
                    continue

                attendance_days = employee.get_attendance_count(start_date, end_date)
                overtime = employee.get_transactions_sum('overtime')
                advance = employee.get_transactions_sum('advance')
                deduction = employee.get_transactions_sum('deduction')
                penalty = employee.get_transactions_sum('penalty')
                daily_allowance = employee.daily_allowance if employee.is_resident else 0

                salary = Salary(
                    employee_id=employee.id,
                    month_year=month_year,
                    base_salary=employee.salary
                )
                salary.calculate(attendance_days, daily_allowance, overtime, advance, deduction, penalty)
                db.session.add(salary)

                for trans in employee.transactions:
                    if not trans.is_settled:
                        trans.is_settled = True
                        trans.settled_date = end_date

                count += 1

            db.session.commit()
            flash(f'تم حساب الرواتب لـ {count} موظف بنجاح', 'success')
            return redirect(url_for('salaries_list'))

        return render_template('financial/salary_calculation.html')

    @app.route('/financial/salaries/pay/<int:salary_id>', methods=['POST'])
    @login_required
    @role_required('admin', 'finance')
    def pay_salary(salary_id):
        salary = Salary.query.get_or_404(salary_id)
        salary.is_paid = True
        salary.paid_date = datetime.now().date()
        salary.payment_method = request.form.get('payment_method')
        salary.payment_reference = request.form.get('payment_reference')
        db.session.commit()
        flash('تم دفع الراتب بنجاح', 'success')
        return redirect(url_for('salaries_list'))

    # ==================== التقييمات ====================
    @app.route('/evaluations')
    @login_required
    def evaluations_list():
        evaluations = Evaluation.query.order_by(Evaluation.date.desc()).all()
        return render_template('evaluations/evaluations.html', evaluations=evaluations)

    @app.route('/evaluations/add', methods=['GET', 'POST'])
    @login_required
    def add_evaluation():
        if request.method == 'POST':
            # حساب المجموع من المعايير
            total_score = 0
            for i in range(1, 8):
                score = request.form.get(f'criteria_{i}', 0)
                if score:
                    total_score += int(score)

            evaluation = Evaluation(
                employee_id=request.form.get('employee_id'),
                evaluator_id=current_user.id,
                evaluation_type='supervisor',
                score=total_score,
                comments=request.form.get('comments'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            )
            db.session.add(evaluation)
            db.session.commit()
            flash('تم إضافة التقييم بنجاح', 'success')
            return redirect(url_for('evaluations_list'))

        # تحديد الشركة بناءً على صلاحية المستخدم
        company_filter = None

        if current_user.role == 'admin':
            # المدير يرى جميع العمال من جميع الشركات (فقط العمال الذين ليس لديهم حساب مستخدم)
            employees = Employee.query.filter(
                Employee.is_active == True,
                Employee.employee_type == 'worker'  # فقط العمال
            ).all()
        else:
            # المشرف: نبحث عن الشركة التابع لها
            supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
            if supervisor_employee and supervisor_employee.company_id:
                company_filter = supervisor_employee.company_id
                employees = Employee.query.filter(
                    Employee.is_active == True,
                    Employee.employee_type == 'worker',  # فقط العمال
                    Employee.company_id == company_filter
                ).all()
            else:
                employees = Employee.query.filter(
                    Employee.is_active == True,
                    Employee.employee_type == 'worker'  # فقط العمال
                ).all()

        # تحويل بيانات العمال إلى JSON مع معلومات إضافية
        employees_data = [{
            'id': e.id,
            'name': e.name,
            'job_title': e.job_title or 'عامل',
            'company_id': e.company_id,
            'company_name': e.employee_company.name if e.employee_company else 'ابن هائل',
            'employee_type': e.employee_type
        } for e in employees]

        # جلب الشركات
        companies = Company.query.all()
        companies_data = [{
            'id': c.id,
            'name': c.name
        } for c in companies]

        # تحويل المناطق إلى JSON
        regions = Region.query.all()
        regions_data = [{
            'id': r.id,
            'name': r.name,
            'company_id': r.company_id
        } for r in regions]

        # تحويل المواقع إلى JSON
        locations = Location.query.all()
        locations_data = [{
            'id': l.id,
            'name': l.name,
            'region_id': l.region_id,
            'address': l.address or ''
        } for l in locations]

        # طباعة للتصحيح
        print("=" * 50)
        print(f"Current User: {current_user.role}")
        print(f"Company Filter: {company_filter}")
        print(f"Employees found: {len(employees_data)}")
        for emp in employees_data:
            print(f"  - {emp['name']} (Company: {emp['company_id']})")
        print("=" * 50)

        return render_template('evaluations/add_evaluation.html',
                               employees=employees_data,
                               companies=companies_data,
                               regions=regions_data,
                               locations=locations_data,
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

    @app.route('/criteria/add', methods=['POST'])
    @login_required
    @role_required('admin')
    def add_criteria():
        """إضافة معيار تقييم جديد لموقع"""
        try:
            location_id = request.form.get('location_id')
            name = request.form.get('name')
            description = request.form.get('description')
            max_score = int(request.form.get('max_score', 10))

            # التحقق من وجود الموقع
            location = Location.query.get_or_404(location_id)

            criteria = EvaluationCriteria(
                location_id=location_id,
                name=name,
                description=description,
                max_score=max_score
            )
            db.session.add(criteria)
            db.session.commit()

            flash('تم إضافة معيار التقييم بنجاح', 'success')
            return redirect(url_for('company_details', company_id=location.region.company_id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('companies_dashboard'))

    @app.route('/criteria/<int:criteria_id>/edit', methods=['POST'])
    @login_required
    @role_required('admin')
    def edit_criteria(criteria_id):
        """تعديل معيار التقييم"""
        try:
            criteria = EvaluationCriteria.query.get_or_404(criteria_id)
            criteria.name = request.form.get('name')
            criteria.description = request.form.get('description')
            criteria.max_score = int(request.form.get('max_score', 10))

            db.session.commit()
            flash('تم تحديث معيار التقييم بنجاح', 'success')
            return redirect(url_for('company_details', company_id=criteria.location.region.company_id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('companies_dashboard'))

    @app.route('/criteria/<int:criteria_id>/delete', methods=['POST'])
    @login_required
    @role_required('admin')
    def delete_criteria(criteria_id):
        """حذف معيار التقييم"""
        try:
            criteria = EvaluationCriteria.query.get_or_404(criteria_id)
            company_id = criteria.location.region.company_id
            db.session.delete(criteria)
            db.session.commit()
            flash('تم حذف معيار التقييم بنجاح', 'success')
            return redirect(url_for('company_details', company_id=company_id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('companies_dashboard'))

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

    @app.route('/contracts')
    @login_required
    def contracts_list():
        contracts = Contract.query.all()
        return render_template('contracts/contracts.html', contracts=contracts)

    @app.route('/contracts/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def add_contract():
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
    def invoices_list():
        invoices = Invoice.query.all()
        return render_template('contracts/invoices.html', invoices=invoices)

    @app.route('/invoices/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def add_invoice():
        if request.method == 'POST':
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

            contract = Contract.query.get(request.form.get('contract_id'))
            if contract:
                contract.amount_received += invoice.amount
                contract.remaining_amount = contract.contract_value - contract.amount_received
                if contract.remaining_amount <= 0:
                    contract.status = 'completed'

            db.session.commit()
            flash('تم إضافة الفاتورة بنجاح', 'success')
            return redirect(url_for('invoices_list'))

        contracts = Contract.query.filter_by(status='active').all()
        return render_template('contracts/add_invoice.html', contracts=contracts)

    @app.route('/invoices/pay/<int:invoice_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'finance')
    def pay_invoice(invoice_id):
        """صفحة تسديد الفاتورة"""
        invoice = Invoice.query.get_or_404(invoice_id)

        if request.method == 'POST':
            try:
                paid_amount = float(request.form.get('paid_amount', 0))
                payment_method = request.form.get('payment_method')
                payment_reference = request.form.get('payment_reference')
                notes = request.form.get('notes', '')

                # التحقق من صحة المبلغ
                remaining = invoice.amount - invoice.paid_amount
                if paid_amount <= 0:
                    flash('المبلغ المدفوع يجب أن يكون أكبر من صفر', 'danger')
                    return redirect(url_for('pay_invoice', invoice_id=invoice_id))

                if paid_amount > remaining:
                    flash(f'المبلغ المدفوع ({paid_amount} ريال) يتجاوز المبلغ المتبقي ({remaining} ريال)', 'danger')
                    return redirect(url_for('pay_invoice', invoice_id=invoice_id))

                # تحديث الفاتورة
                invoice.paid_amount += paid_amount
                invoice.payment_method = payment_method
                invoice.payment_reference = payment_reference
                invoice.notes = notes + (
                    f'\nتسديد بتاريخ {datetime.now().strftime("%Y-%m-%d")}' if invoice.notes else f'تسديد بتاريخ {datetime.now().strftime("%Y-%m-%d")}')

                # إذا تم دفع كامل المبلغ
                if invoice.paid_amount >= invoice.amount:
                    invoice.is_paid = True
                    invoice.paid_date = datetime.now().date()
                    flash('تم تسديد كامل قيمة الفاتورة بنجاح', 'success')
                else:
                    flash(
                        f'تم تسديد مبلغ {paid_amount:,.0f} ريال، المتبقي {invoice.amount - invoice.paid_amount:,.0f} ريال',
                        'success')

                # تحديث العقد
                contract = invoice.contract
                if contract:
                    # حساب إجمالي المدفوعات لهذا العقد
                    total_paid = sum(i.paid_amount for i in contract.invoices)
                    contract.amount_received = total_paid
                    contract.remaining_amount = contract.contract_value - total_paid

                    if contract.remaining_amount <= 0:
                        contract.status = 'completed'
                    elif contract.status == 'completed':
                        contract.status = 'active'

                    db.session.commit()

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash(f'حدث خطأ: {str(e)}', 'danger')

            return redirect(url_for('invoices_list'))

        # حساب المتبقي
        remaining_amount = invoice.amount - (invoice.paid_amount or 0)

        return render_template('contracts/pay_invoice.html',
                               invoice=invoice,
                               remaining_amount=remaining_amount,
                               now=datetime.now())

    @app.route('/invoices/partial_payments/<int:invoice_id>')
    @login_required
    def invoice_partial_payments(invoice_id):
        """عرض سجل المدفوعات الجزئية للفاتورة"""
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template('contracts/invoice_payments.html', invoice=invoice)

    # ==================== التقارير ====================

    @app.route('/reports/attendance')
    @login_required
    def attendance_report():
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id', type=int)  # أضف هذا

        query = Attendance.query
        if start_date:
            query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)

        attendances = query.all()
        employees = Employee.query.filter_by(is_active=True).all()  # أضف هذا للفلترة في القالب

        return render_template('reports/attendance_report.html',
                               attendances=attendances,
                               employees=employees)  # أضف employees

    @app.route('/reports/financial')
    @login_required
    @role_required('admin', 'finance')
    def financial_report():
        """تقرير مالي - يعرض رواتب شهر محدد أو جميع الأشهر"""
        month_year = request.args.get('month_year')

        # الحصول على قائمة الأشهر المتاحة
        all_salaries_list = Salary.query.all()
        available_months = list(set([s.month_year for s in all_salaries_list]))
        available_months.sort(reverse=True)

        # إذا كان month_year = 'all' أو لم يتم تحديد شهر
        if month_year == 'all' or not month_year:
            # عرض جميع الرواتب
            salaries = Salary.query.order_by(Salary.month_year.desc()).all()

            if salaries:
                total_salaries = sum(s.total_salary for s in salaries)
                total_attendance_days = sum(s.attendance_days for s in salaries)
                paid_salaries = sum(1 for s in salaries if s.is_paid)

                report = {
                    'month_year': 'جميع الأشهر',
                    'start_date': None,
                    'end_date': None,
                    'total_employees': len(salaries),
                    'total_attendance_days': total_attendance_days,
                    'total_salaries': total_salaries,
                    'paid_salaries': paid_salaries,
                    'salaries': salaries
                }
                return render_template('reports/financial_report.html',
                                       report=report,
                                       available_months=available_months,
                                       selected_month='all',
                                       now=datetime.now())

        elif month_year:
            # عرض رواتب شهر محدد
            salaries = Salary.query.filter_by(month_year=month_year).all()

            if salaries:
                start_date, end_date = get_financial_month_dates(month_year)

                total_salaries = sum(s.total_salary for s in salaries)
                total_attendance_days = sum(s.attendance_days for s in salaries)
                paid_salaries = sum(1 for s in salaries if s.is_paid)

                report = {
                    'month_year': month_year,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_employees': len(salaries),
                    'total_attendance_days': total_attendance_days,
                    'total_salaries': total_salaries,
                    'paid_salaries': paid_salaries,
                    'salaries': salaries
                }
                return render_template('reports/financial_report.html',
                                       report=report,
                                       available_months=available_months,
                                       selected_month=month_year,
                                       now=datetime.now())

        return render_template('reports/financial_report.html',
                               available_months=available_months,
                               selected_month=None,
                               now=datetime.now())

    @app.route('/reports/employees')
    @login_required
    def employees_report():
        employees = Employee.query.all()
        return render_template('reports/employees_report.html', employees=employees)

    @app.route('/reports/regions')
    @login_required
    def regions_report():
        # جلب المناطق من الشركات
        regions_result = db.session.query(
            Company.region,
            db.func.count(Company.id).label('companies_count')
        ).filter(
            Company.region != None,
            Company.region != ''
        ).group_by(Company.region).all()

        # تحويل إلى قائمة قواميس
        regions_data = []
        total_employees = 0

        for row in regions_result:
            region_name = row[0]
            companies_count = row[1]

            # جلب جميع الشركات في هذه المنطقة
            companies_in_region = Company.query.filter_by(region=region_name).all()

            # حساب عدد الموظفين في هذه المنطقة
            employees_count = 0
            for company in companies_in_region:
                employees_count += Employee.query.filter_by(company_id=company.id, is_active=True).count()

            total_employees += employees_count

            regions_data.append({
                'region': region_name,
                'companies_count': companies_count,
                'employees_count': employees_count
            })

        # ترتيب حسب عدد الموظفين (تنازلي)
        regions_data.sort(key=lambda x: x['employees_count'], reverse=True)

        return render_template('reports/regions_report.html',
                               regions_data=regions_data,
                               total_employees=total_employees)

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
        expenses = Expense.query.filter(
            Expense.date >= start_date,
            Expense.date <= end_date
        ).all()
        expenses_total = sum(e.amount for e in expenses)

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