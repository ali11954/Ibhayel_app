from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import (
    db, Employee, Attendance, Company, Salary,
    AttendancePeriodTransfer, AttendancePeriodTransferDetail,
    JournalEntry
)
from utils import (
    role_required, get_regions,
    get_employee_attendance_summary, get_employee_overtime_hours
)

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/')
@login_required
def attendance_list():
    today = datetime.now().date()
    date = request.args.get('date', today.strftime('%Y-%m-%d'))
    selected_date = datetime.strptime(date, '%Y-%m-%d').date()

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    attendances = Attendance.query.options(
        db.load_only(Attendance.employee_id, Attendance.attendance_status,
                     Attendance.late_minutes, Attendance.check_in_time,
                     Attendance.check_out_time, Attendance.notes,
                     Attendance.sick_leave_days, Attendance.annual_leave_days)
    ).filter_by(date=selected_date).all()

    attendance_dict = {a.employee_id: a for a in attendances}

    employee_query = Employee.query.filter_by(is_active=True).options(
        db.load_only(Employee.id, Employee.name, Employee.job_title,
                     Employee.card_number, Employee.phone, Employee.company_id,
                     Employee.region, Employee.is_resident, Employee.salary,
                     Employee.employee_type)
    )

    if current_user.role == 'admin':
        employees = employee_query.all()
    elif current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            employees = employee_query.filter_by(company_id=supervisor_employee.company_id).all()
        else:
            employees = []
    else:
        employees = []

    regions = get_regions()
    companies = Company.query.options(
        db.load_only(Company.id, Company.name)
    ).all()

    for emp in employees:
        if not hasattr(emp, 'remaining_annual_leave'):
            emp.remaining_annual_leave = 30

    return render_template('attendance/attendance.html',
                           attendance_dict=attendance_dict,
                           employees=employees,
                           selected_date=selected_date,
                           prev_date=prev_date.strftime('%Y-%m-%d'),
                           next_date=next_date.strftime('%Y-%m-%d'),
                           today=today.strftime('%Y-%m-%d'),
                           regions=regions,
                           companies=companies,
                           now=datetime.now())


@attendance_bp.route('/add', methods=['POST'])
@login_required
def add_attendance():
    try:
        employee_id = request.form.get('employee_id')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        attendance_status = request.form.get('attendance_status', 'present')

        employee = Employee.query.get(employee_id)
        if not employee:
            flash('الموظف غير موجود', 'danger')
            return redirect(url_for('attendance.attendance_list'))

        check_in_time = None
        if request.form.get('check_in_time'):
            check_in_time = datetime.strptime(request.form.get('check_in_time'), '%H:%M').time()

        check_out_time = None
        if request.form.get('check_out_time'):
            check_out_time = datetime.strptime(request.form.get('check_out_time'), '%H:%M').time()

        existing = Attendance.query.filter_by(employee_id=employee_id, date=date).first()

        if existing:
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

    return redirect(url_for('attendance.attendance_list', date=date))


@attendance_bp.route('/remove', methods=['POST'])
@login_required
def remove_attendance():
    employee_id = request.form.get('employee_id')
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

    attendance = Attendance.query.filter_by(employee_id=employee_id, date=date).first()
    if attendance:
        db.session.delete(attendance)
        db.session.commit()
        flash('تم إزالة الحضور بنجاح', 'success')

    return redirect(url_for('attendance.attendance_list', date=date))


@attendance_bp.route('/group', methods=['POST'])
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
        return redirect(url_for('attendance.attendance_list', date=date))

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
    return redirect(url_for('attendance.attendance_list', date=date))


@attendance_bp.route('/edit/<int:attendance_id>', methods=['GET', 'POST'])
@login_required
def edit_attendance_record(attendance_id):
    attendance = Attendance.query.get_or_404(attendance_id)

    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    employee_id = request.args.get('employee_id', '')

    if request.method == 'POST':
        try:
            attendance.attendance_status = request.form.get('attendance_status')
            attendance.attendance_type = request.form.get('attendance_type')
            attendance.late_minutes = int(request.form.get('late_minutes', 0))

            if request.form.get('check_in_time'):
                attendance.check_in_time = datetime.strptime(request.form.get('check_in_time'), '%H:%M').time()
            else:
                attendance.check_in_time = None

            if request.form.get('check_out_time'):
                attendance.check_out_time = datetime.strptime(request.form.get('check_out_time'), '%H:%M').time()
            else:
                attendance.check_out_time = None

            attendance.notes = request.form.get('notes', '')

            attendance.sick_leave = attendance.attendance_status == 'sick'
            if attendance.attendance_status == 'sick':
                attendance.sick_leave_days = int(request.form.get('sick_leave_days', 1))
            else:
                attendance.sick_leave_days = 0

            db.session.commit()
            flash('تم تحديث سجل الحضور بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('attendance_report',
                                start_date=request.form.get('start_date'),
                                end_date=request.form.get('end_date'),
                                employee_id=request.form.get('employee_id')))

    return render_template('attendance/edit_attendance.html',
                           attendance=attendance,
                           start_date=start_date,
                           end_date=end_date,
                           employee_id=employee_id)


@attendance_bp.route('/bulk_save', methods=['POST'])
@login_required
def save_bulk_attendance():
    try:
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        employee_ids = request.form.getlist('employee_ids')

        count = 0
        for emp_id in employee_ids:
            status = request.form.get(f'status_{emp_id}')
            employee = Employee.query.get(emp_id)

            if not status or not employee:
                continue

            existing = Attendance.query.filter_by(employee_id=emp_id, date=date).first()

            if status == 'absent':
                if existing:
                    db.session.delete(existing)
                continue

            check_in_time = None
            if request.form.get(f'check_in_time_{emp_id}'):
                check_in_time = datetime.strptime(request.form.get(f'check_in_time_{emp_id}'), '%H:%M').time()

            check_out_time = None
            if request.form.get(f'check_out_time_{emp_id}'):
                check_out_time = datetime.strptime(request.form.get(f'check_out_time_{emp_id}'), '%H:%M').time()

            late_minutes = int(request.form.get(f'late_minutes_{emp_id}', 0)) if status == 'late' else 0
            sick_leave_days = int(request.form.get(f'sick_leave_days_{emp_id}', 0)) if status == 'sick' else 0

            annual_leave_days = 0
            days_before = 0

            if status == 'annual_leave_paid':
                annual_leave_days = int(request.form.get(f'annual_leave_days_{emp_id}', 1))
                if employee.remaining_annual_leave is None:
                    employee.remaining_annual_leave = 30
                days_before = employee.remaining_annual_leave
                employee.remaining_annual_leave -= annual_leave_days
                status = 'annual_leave'

            elif status == 'annual_leave_unpaid':
                annual_leave_days = int(request.form.get(f'annual_leave_unpaid_days_{emp_id}', 1))
                status = 'annual_leave_unpaid'
            else:
                annual_leave_days = int(
                    request.form.get(f'annual_leave_days_{emp_id}', 0)) if status == 'annual_leave' else 0

            if existing:
                existing.attendance_status = status
                existing.late_minutes = late_minutes
                existing.sick_leave = status == 'sick'
                existing.sick_leave_days = sick_leave_days
                existing.annual_leave_days = annual_leave_days
                existing.check_in_time = check_in_time
                existing.check_out_time = check_out_time
                existing.notes = request.form.get(f'notes_{emp_id}', '')
            else:
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

    return redirect(url_for('attendance.attendance_list', date=date))


@attendance_bp.route('/delete/<int:attendance_id>', methods=['POST'])
@login_required
def delete_attendance_record(attendance_id):
    attendance = Attendance.query.get_or_404(attendance_id)

    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    employee_id = request.form.get('employee_id', '')

    try:
        db.session.delete(attendance)
        db.session.commit()
        flash('تم حذف سجل الحضور بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('attendance_report',
                            start_date=start_date,
                            end_date=end_date,
                            employee_id=employee_id))


@attendance_bp.route('/period-transfer/create-management')
@login_required
@role_required('admin', 'finance')
def create_management_transfer():
    from utils import create_management_salary_transfer

    result = create_management_salary_transfer()

    if result['success']:
        flash(f"✅ {result['message']}", 'success')
        flash(f"📋 الفترة: {result['start_date']} إلى {result['end_date']}", 'info')
        for emp in result['employees']:
            flash(f"   👤 {emp['type']}: {emp['name']} - الراتب: {emp['salary']:,.0f} ريال", 'info')
        return redirect(url_for('attendance.view_period_transfer', transfer_id=result['transfer_id']))
    else:
        flash(f"❌ {result['message']}", 'danger')
        return redirect(url_for('attendance.period_transfer_list'))


@attendance_bp.route('/period-transfer')
@login_required
@role_required('admin', 'finance')
def period_transfer_list():
    transfers = AttendancePeriodTransfer.query.order_by(AttendancePeriodTransfer.start_date.desc()).all()
    return render_template('attendance/period_transfers_list.html', transfers=transfers)


@attendance_bp.route('/period-transfer/transfer-to-salary/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def transfer_period_to_salary(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    if transfer.is_transferred:
        flash('تم ترحيل هذه الفترة مسبقاً', 'danger')
        return redirect(url_for('attendance.period_transfer_list'))

    try:
        start_date = transfer.start_date
        end_date = transfer.end_date
        period_name = transfer.period_name
        count = 0

        for detail in transfer.transfers_details:
            employee = detail.employee

            period_days = (end_date - start_date).days + 1
            daily_rate = employee.salary / 30

            daily_allowance = 0
            if employee.is_resident:
                daily_rate_allowance = getattr(employee, 'daily_allowance', 500)
                daily_allowance = detail.attendance_days * daily_rate_allowance

            hourly_rate = employee.salary / 30 / 8
            overtime_amount = detail.overtime_hours * (hourly_rate * 1.5)

            from models import FinancialTransaction

            settled_transactions = FinancialTransaction.query.filter(
                FinancialTransaction.employee_id == employee.id,
                FinancialTransaction.is_settled == True,
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            ).all()

            advances = sum(t.amount for t in settled_transactions if t.transaction_type == 'advance')
            penalties = sum(t.amount for t in settled_transactions if t.transaction_type == 'penalty')
            overtime_from_trans = sum(t.amount for t in settled_transactions if t.transaction_type == 'overtime')

            cafeteria_deductions = sum(t.amount for t in settled_transactions if t.transaction_type == 'cafeteria')
            restaurant_deductions = sum(
                t.amount for t in settled_transactions if t.transaction_type == 'restaurant')

            total_overtime = overtime_amount + overtime_from_trans

            attendance_amount = daily_rate * detail.attendance_days

            total_deductions = advances + penalties + cafeteria_deductions + restaurant_deductions

            total_salary = attendance_amount + daily_allowance + total_overtime - total_deductions

            period_key = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            period_display = f"فترة من {start_date.strftime('%d/%m/%Y')} إلى {end_date.strftime('%d/%m/%Y')}"

            existing = Salary.query.filter_by(
                employee_id=employee.id,
                month_year=period_key
            ).first()

            if existing:
                existing.attendance_days = detail.attendance_days
                existing.attendance_amount = attendance_amount
                existing.overtime_amount = total_overtime
                existing.daily_allowance_amount = daily_allowance
                existing.advance_amount = advances
                existing.penalty_amount = penalties
                existing.cafeteria_deduction = cafeteria_deductions
                existing.restaurant_deduction = restaurant_deductions
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
                    overtime_amount=total_overtime,
                    advance_amount=advances,
                    penalty_amount=penalties,
                    cafeteria_deduction=cafeteria_deductions,
                    restaurant_deduction=restaurant_deductions,
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

    return redirect(url_for('attendance.period_transfer_list'))


@attendance_bp.route('/period-transfer/refresh/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def refresh_period_transfer(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    if transfer.is_transferred:
        flash('⚠️ لا يمكن تحديث فترة تم ترحيلها بالفعل', 'danger')
        return redirect(url_for('attendance.period_transfer_list'))

    try:
        start_date = transfer.start_date
        end_date = transfer.end_date

        for detail in transfer.transfers_details:
            db.session.delete(detail)

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
            return redirect(url_for('attendance.period_transfer_list'))

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

    return redirect(url_for('attendance.view_period_transfer', transfer_id=transfer.id))


@attendance_bp.route('/period-transfer/view/<int:transfer_id>')
@login_required
@role_required('admin', 'finance')
def view_period_transfer(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

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


@attendance_bp.route('/period-transfer/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def create_period_transfer():
    if request.method == 'POST':
        period_name = request.form.get('period_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        company_id = request.form.get('company_id')
        region = request.form.get('region')
        payroll_type = request.form.get('payroll_type', 'labor')

        if start_date > end_date:
            flash('تاريخ البداية يجب أن يكون قبل تاريخ النهاية', 'danger')
            return redirect(url_for('attendance.create_period_transfer'))

        query = AttendancePeriodTransfer.query.filter(
            AttendancePeriodTransfer.payroll_type == payroll_type,
            AttendancePeriodTransfer.start_date <= end_date,
            AttendancePeriodTransfer.end_date >= start_date
        )

        if company_id:
            existing = query.filter(AttendancePeriodTransfer.company_id == company_id).first()
            if existing:
                flash(
                    f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لنفس الشركة من {existing.start_date} إلى {existing.end_date}',
                    'danger')
                return redirect(url_for('attendance.create_period_transfer'))
        elif region:
            existing = query.filter(AttendancePeriodTransfer.region == region).first()
            if existing:
                flash(
                    f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لنفس المنطقة من {existing.start_date} إلى {existing.end_date}',
                    'danger')
                return redirect(url_for('attendance.create_period_transfer'))
        else:
            existing = query.filter(
                AttendancePeriodTransfer.company_id == None,
                AttendancePeriodTransfer.region == None
            ).first()
            if existing:
                flash(
                    f'❌ لا يمكن إنشاء الترحيل: هناك فترة مكررة أو متداخلة لرواتب {existing.get_payroll_type_name()} لجميع الموظفين من {existing.start_date} إلى {existing.end_date}',
                    'danger')
                return redirect(url_for('attendance.create_period_transfer'))

        transfer = AttendancePeriodTransfer(
            period_name=period_name,
            payroll_type=payroll_type,
            start_date=start_date,
            end_date=end_date,
            transfer_date=datetime.now().date(),
            transferred_by=current_user.id,
            company_id=company_id if company_id else None,
            region=region if region else None
        )
        db.session.add(transfer)
        db.session.commit()

        query = Employee.query.filter_by(is_active=True)

        if payroll_type == 'admin':
            query = query.filter(Employee.employee_type.in_(['admin', 'supervisor']))
        else:
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
            return redirect(url_for('attendance.create_period_transfer'))

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

        flash(f'✅ تم إنشاء ترحيل فترة الدوام لـ {count} موظف في {filter_desc} من {start_date} إلى {end_date}',
              'success')
        return redirect(url_for('attendance.view_period_transfer', transfer_id=transfer.id))

    companies = Company.query.all()
    regions = get_regions()

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


@attendance_bp.route('/period-transfer/delete/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def delete_period_transfer(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    try:
        if transfer.is_transferred:
            period_key = f"{transfer.start_date.strftime('%Y%m%d')}_{transfer.end_date.strftime('%Y%m%d')}"
            salaries = Salary.query.filter_by(month_year=period_key).all()

            for salary in salaries:
                journal_entry = JournalEntry.query.filter_by(
                    reference_type='salary_payment',
                    reference_id=salary.id
                ).first()
                if journal_entry:
                    db.session.delete(journal_entry)

                accrual_entry = JournalEntry.query.filter(
                    JournalEntry.reference_type == 'salary',
                    JournalEntry.reference_id == salary.id
                ).first()
                if accrual_entry:
                    db.session.delete(accrual_entry)

                db.session.delete(salary)

        for detail in transfer.transfers_details:
            db.session.delete(detail)

        db.session.delete(transfer)
        db.session.commit()

        return jsonify({'success': True, 'message': 'تم حذف الفترة بنجاح'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_bp.route('/period-transfer/refresh/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def refresh_period_transfer_api(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    if transfer.is_transferred:
        return jsonify({'success': False, 'error': 'لا يمكن تحديث فترة تم ترحيلها بالفعل'}), 400

    try:
        start_date = transfer.start_date
        end_date = transfer.end_date

        for detail in transfer.transfers_details:
            db.session.delete(detail)
        db.session.flush()

        query = Employee.query.filter_by(is_active=True)

        if transfer.company_id:
            query = query.filter_by(company_id=transfer.company_id)
        elif transfer.region:
            query = query.filter_by(region=transfer.region)
        else:
            query = query.filter(Employee.employee_type == 'worker')

        employees = query.all()

        if not employees:
            db.session.rollback()
            return jsonify({'success': False, 'error': 'لا يوجد موظفين في هذا الفلتر'}), 400

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

        return jsonify({'success': True, 'message': f'تم تحديث {count} موظف بنجاح'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@attendance_bp.route('/period-transfer/edit/<int:transfer_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def edit_period_transfer(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    if transfer.is_transferred:
        flash('لا يمكن تعديل فترة تم ترحيلها بالفعل', 'danger')
        return redirect(url_for('attendance.period_transfer_list'))

    if request.method == 'POST':
        try:
            transfer.period_name = request.form.get('period_name')
            transfer.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            transfer.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

            db.session.commit()
            flash('✅ تم تحديث الفترة بنجاح', 'success')
            return redirect(url_for('attendance.view_period_transfer', transfer_id=transfer.id))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return render_template('attendance/edit_period_transfer.html', transfer=transfer)


@attendance_bp.route('/period-transfer/force-delete/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def force_delete_period_transfer(transfer_id):
    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

    try:
        deleted_items = {
            'salaries': 0,
            'journal_entries': 0,
            'transfer_details': 0
        }

        if transfer.is_transferred:
            period_key = f"{transfer.start_date.strftime('%Y%m%d')}_{transfer.end_date.strftime('%Y%m%d')}"

            salaries = Salary.query.filter(
                Salary.month_year == period_key
            ).all()

            if not salaries:
                alt_key = transfer.start_date.strftime('%m-%Y')
                salaries = Salary.query.filter(
                    Salary.month_year == alt_key
                ).all()

            for salary in salaries:
                deleted_items['salaries'] += 1

                payment_entry = JournalEntry.query.filter_by(
                    reference_type='salary_payment',
                    reference_id=salary.id
                ).first()
                if payment_entry:
                    db.session.delete(payment_entry)
                    deleted_items['journal_entries'] += 1

                accrual_entry = JournalEntry.query.filter(
                    JournalEntry.reference_type == 'salary',
                    JournalEntry.reference_id == salary.id
                ).first()
                if accrual_entry:
                    db.session.delete(accrual_entry)
                    deleted_items['journal_entries'] += 1

                accrual_entry2 = JournalEntry.query.filter(
                    JournalEntry.reference_type == 'salary_accrual',
                    JournalEntry.reference_id == salary.id
                ).first()
                if accrual_entry2:
                    db.session.delete(accrual_entry2)
                    deleted_items['journal_entries'] += 1

                db.session.delete(salary)

        for detail in transfer.transfers_details:
            db.session.delete(detail)
            deleted_items['transfer_details'] += 1

        period_name = transfer.period_name
        db.session.delete(transfer)

        db.session.commit()

        message = f'تم حذف الفترة "{period_name}" بنجاح'
        if deleted_items['salaries'] > 0:
            message += f' (تم حذف {deleted_items["salaries"]} راتب و {deleted_items["journal_entries"]} قيد محاسبي)'

        return jsonify({
            'success': True,
            'message': message,
            'deleted': deleted_items
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
