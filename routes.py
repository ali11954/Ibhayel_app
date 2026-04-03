# routes.py
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd

from models import db, User, Employee, Attendance, FinancialTransaction, Salary
from models import Evaluation, Company, Contract, Invoice
from utils import role_required, get_financial_month_dates, format_currency, get_regions
from config import Config

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
    # ==================== إدارة الموظفين ====================
    @app.route('/employees')
    @login_required
    def employees_list():
        employees = Employee.query.filter_by(is_active=True).all()
        regions = get_regions()
        companies = Company.query.all()  # جلب الشركات للفلترة
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
            # التحقق من عدم وجود نفس الرقم أو الكود
            card_number = request.form.get('card_number')
            code = request.form.get('code')

            existing_card = Employee.query.filter_by(card_number=card_number).first()
            if existing_card:
                flash('رقم البطاقة موجود مسبقاً', 'danger')
                companies = Company.query.all()
                return render_template('employees/add_employee.html', companies=companies)

            existing_code = Employee.query.filter_by(code=code).first()
            if existing_code:
                flash('كود التعريف موجود مسبقاً', 'danger')
                companies = Company.query.all()
                return render_template('employees/add_employee.html', companies=companies)

            employee = Employee(
                name=request.form.get('name'),
                card_number=card_number,
                code=code,
                job_title=request.form.get('job_title'),
                region=request.form.get('region'),
                is_resident=request.form.get('is_resident') == 'on',
                phone=request.form.get('phone'),
                salary=float(request.form.get('salary', 60000)),
                company_id=request.form.get('company_id') or None
            )
            db.session.add(employee)
            db.session.commit()
            flash('تم إضافة الموظف بنجاح', 'success')
            return redirect(url_for('employees_list'))

        # جلب قائمة الشركات
        companies = Company.query.all()
        return render_template('employees/add_employee.html', companies=companies)

    @app.route('/employees/edit/<int:emp_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'supervisor')
    def edit_employee(emp_id):
        employee = Employee.query.get_or_404(emp_id)

        if request.method == 'POST':
            # التحقق من عدم وجود نفس الرقم أو الكود (باستثناء الموظف الحالي)
            card_number = request.form.get('card_number')
            code = request.form.get('code')

            existing_card = Employee.query.filter(
                Employee.card_number == card_number,
                Employee.id != emp_id
            ).first()
            if existing_card:
                flash('رقم البطاقة موجود مسبقاً لمستخدم آخر', 'danger')
                companies = Company.query.all()
                return render_template('employees/edit_employee.html',
                                       employee=employee,
                                       companies=companies)

            existing_code = Employee.query.filter(
                Employee.code == code,
                Employee.id != emp_id
            ).first()
            if existing_code:
                flash('كود التعريف موجود مسبقاً لمستخدم آخر', 'danger')
                companies = Company.query.all()
                return render_template('employees/edit_employee.html',
                                       employee=employee,
                                       companies=companies)

            employee.name = request.form.get('name')
            employee.card_number = card_number
            employee.code = code
            employee.job_title = request.form.get('job_title')
            employee.region = request.form.get('region')
            employee.is_resident = request.form.get('is_resident') == 'on'
            employee.phone = request.form.get('phone')
            employee.salary = float(request.form.get('salary', 60000))
            employee.company_id = request.form.get('company_id') or None

            db.session.commit()
            flash('تم تحديث الموظف بنجاح', 'success')
            return redirect(url_for('employees_list'))

        companies = Company.query.all()
        return render_template('employees/edit_employee.html',
                               employee=employee,
                               companies=companies)

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

    @app.route('/companies/dashboard')
    @login_required
    def companies_dashboard():
        """لوحة الشركات الرئيسية"""
        companies = Company.query.all()
        companies_count = len(companies)

        # حساب عدد الموظفين لكل شركة
        for company in companies:
            company.employee_count = Employee.query.filter_by(company_id=company.id, is_active=True).count()

        # العقود النشطة
        active_contracts = Contract.query.filter_by(status='active').count()

        # إجمالي الفواتير
        total_invoices = db.session.query(func.sum(Invoice.amount)).scalar() or 0

        return render_template('companies/dashboard.html',
                               companies=companies,
                               companies_count=companies_count,
                               active_contracts=active_contracts,
                               total_invoices_amount=total_invoices)

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
            evaluation = Evaluation(
                employee_id=request.form.get('employee_id'),
                evaluator_id=current_user.id,
                evaluation_type=request.form.get('evaluation_type'),
                score=int(request.form.get('score')),
                comments=request.form.get('comments'),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            )
            db.session.add(evaluation)
            db.session.commit()
            flash('تم إضافة التقييم بنجاح', 'success')
            return redirect(url_for('evaluations_list'))

        employees = Employee.query.filter_by(is_active=True).all()
        return render_template('evaluations/add_evaluation.html',
                               employees=employees,
                               evaluation_types=Evaluation.EVALUATION_TYPES)

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

    # ==================== الشركات والعقود ====================
    @app.route('/companies')
    @login_required
    def companies_list():
        companies = Company.query.all()

        # حساب عدد الموظفين لكل شركة
        for company in companies:
            company.employee_count = Employee.query.filter_by(company_id=company.id, is_active=True).count()

        return render_template('companies/companies.html', companies=companies)

    @app.route('/companies/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin')
    def add_company():
        if request.method == 'POST':
            company = Company(
                name=request.form.get('name'),
                region=request.form.get('region'),
                location=request.form.get('location'),
                contact_person=request.form.get('contact_person'),
                phone=request.form.get('phone'),
                email=request.form.get('email')
            )
            db.session.add(company)
            db.session.commit()
            flash('تم إضافة الشركة بنجاح', 'success')
            return redirect(url_for('companies_list'))
        return render_template('companies/add_company.html')

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
