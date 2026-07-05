from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import Employee, Company, User, Region, Location, db
from utils import role_required, get_regions
import pandas as pd

employees_bp = Blueprint('employees', __name__, url_prefix='/employees')


def get_supervisor_workers():
    if current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id, is_active=True).first()
        if supervisor_employee:
            return Employee.query.filter(
                Employee.is_active == True,
                Employee.supervisor_id == supervisor_employee.id
            ).all()
    return []


def can_edit_employee(employee):
    if current_user.role == 'admin':
        return True
    elif current_user.role == 'supervisor':
        return False
    return False


def can_delete_employee(employee):
    if current_user.role == 'admin':
        return True
    return False


@employees_bp.route('')
@login_required
def employees_list():
    from sqlalchemy.orm import joinedload

    if current_user.role == 'admin':
        employees = Employee.query.options(
            joinedload(Employee.employee_company),
            joinedload(Employee.supervisor)
        ).filter_by(is_active=True).all()
    elif current_user.role == 'supervisor':
        employees = get_supervisor_workers()
    else:
        employees = []

    regions = get_regions()
    companies = Company.query.all()

    total_employees = len(employees)
    resident_count = sum(1 for e in employees if e.is_resident)
    non_resident_count = total_employees - resident_count
    companies_count = len(companies)

    total_basic_salaries = sum(e.salary for e in employees)
    total_total_salaries = sum(e.total_salary if e.total_salary is not None else e.salary for e in employees)

    avg_basic_salary = total_basic_salaries / total_employees if total_employees > 0 else 0

    daily_allowance_total = resident_count * 500

    stats = {
        'total_employees': total_employees,
        'resident_count': resident_count,
        'non_resident_count': non_resident_count,
        'companies_count': companies_count,
        'total_basic_salaries': total_basic_salaries,
        'total_basic_salaries_formatted': f"{total_basic_salaries:,.0f} ر.ي",
        'total_total_salaries': total_total_salaries,
        'total_total_salaries_formatted': f"{total_total_salaries:,.0f} ر.ي",
        'avg_basic_salary': avg_basic_salary,
        'avg_basic_salary_formatted': f"{avg_basic_salary:,.0f} ر.ي",
        'daily_allowance_total': f"{daily_allowance_total:,.0f}"
    }

    return render_template('employees/employees.html',
                           employees=employees,
                           regions=regions,
                           companies=companies,
                           stats=stats,
                           can_edit=(current_user.role == 'admin'),
                           can_delete=(current_user.role == 'admin'))


@employees_bp.route('/import', methods=['GET', 'POST'])
@login_required
@role_required('admin')
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

                    basic_salary = float(row.get('الراتب الأساسي', 60000)) if pd.notna(
                        row.get('الراتب الأساسي')) else 60000
                    total_salary = float(row.get('الراتب الشامل', basic_salary)) if pd.notna(
                        row.get('الراتب الشامل')) else basic_salary

                    employee = Employee(
                        name=row['الاســــــم'],
                        card_number=str(row['رقم البطاقة']),
                        code=str(row.get('كود تعريف', '')),
                        job_title=row.get('الوظيفة', ''),
                        region=row.get('المنطقة', ''),
                        is_resident=row.get('ميزة ساكن') == 'ساكن' if pd.notna(row.get('ميزة ساكن')) else False,
                        phone=str(row.get('رقم الجوال', '')),
                        salary=basic_salary,
                        total_salary=total_salary,
                        company_id=company.id if company else None
                    )
                    db.session.add(employee)
                    count += 1
            db.session.commit()
            flash(f'تم استيراد {count} موظف بنجاح', 'success')
            return redirect(url_for('employees.employees_list'))
        flash('الرجاء اختيار ملف Excel صحيح', 'danger')

    companies = Company.query.all()
    return render_template('employees/import_employees.html', companies=companies)


@employees_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_employee():
    if request.method == 'POST':
        card_number = request.form.get('card_number')
        code = request.form.get('code')
        employee_type = request.form.get('employee_type')
        supervisor_id = request.form.get('supervisor_id')

        basic_salary = float(request.form.get('salary', 60000))
        total_salary = float(request.form.get('total_salary', basic_salary))

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
                salary=basic_salary,
                total_salary=total_salary,
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

            return redirect(url_for('employees.employees_list'))

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


@employees_bp.route('/edit/<int:emp_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_employee(emp_id):
    employee = Employee.query.get_or_404(emp_id)
    old_employee_type = employee.employee_type
    old_supervisor_id = employee.supervisor_id

    if request.method == 'POST':
        card_number = request.form.get('card_number')
        code = request.form.get('code')
        employee_type = request.form.get('employee_type')
        supervisor_id = request.form.get('supervisor_id')

        basic_salary = float(request.form.get('salary', 60000))
        total_salary = float(request.form.get('total_salary', basic_salary))

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
        employee.salary = basic_salary
        employee.total_salary = total_salary
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

        return redirect(url_for('employees.employees_list'))

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


@employees_bp.route('/delete/<int:emp_id>')
@login_required
@role_required('admin')
def delete_employee(emp_id):
    employee = Employee.query.get_or_404(emp_id)
    employee.is_active = False
    db.session.commit()
    flash('تم حذف الموظف بنجاح', 'success')
    return redirect(url_for('employees.employees_list'))


@employees_bp.route('/api/list')
@login_required
def employees_api():
    employees = Employee.query.filter_by(is_active=True).all()
    return jsonify([e.to_dict() for e in employees])


@employees_bp.route('/api/company/<int:company_id>')
@login_required
def employees_by_company_api(company_id):
    employees = Employee.query.filter_by(is_active=True, company_id=company_id).all()
    return jsonify([e.to_dict() for e in employees])


@employees_bp.route('/check_card', methods=['POST'])
@login_required
def check_card_number():
    data = request.get_json()
    card_number = data.get('card_number')
    employee_id = data.get('employee_id')

    query = Employee.query.filter_by(card_number=card_number)
    if employee_id:
        query = query.filter(Employee.id != employee_id)

    exists = query.first() is not None
    return jsonify({'exists': exists})


@employees_bp.route('/check_code', methods=['POST'])
@login_required
def check_employee_code():
    data = request.get_json()
    code = data.get('code')
    employee_id = data.get('employee_id')

    query = Employee.query.filter_by(code=code)
    if employee_id:
        query = query.filter(Employee.id != employee_id)

    exists = query.first() is not None
    return jsonify({'exists': exists})
