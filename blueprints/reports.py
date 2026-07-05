from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import (
    db, Employee, Attendance, Salary, Company, Evaluation, Region, Location,
    AttendancePeriodTransfer, FinancialTransaction
)
from utils import role_required, get_financial_month_dates, get_regions
import pandas as pd
from io import BytesIO

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

reports_bp = Blueprint('reports_bp', __name__)


def _format_period_display(salary):
    if salary.notes and 'فترة من' in salary.notes:
        return salary.notes
    elif '_' in salary.month_year:
        parts = salary.month_year.split('_')
        if len(parts) == 2:
            try:
                start = datetime.strptime(parts[0], '%Y%m%d').date()
                end = datetime.strptime(parts[1], '%Y%m%d').date()
                return f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}"
            except:
                pass
    return salary.month_year


@reports_bp.route('/reports/dashboard')
@login_required
def reports_dashboard():
    from sqlalchemy import func

    if current_user.role == 'admin':
        total_employees = Employee.query.filter_by(is_active=True).count()
        total_companies = Company.query.count()
        today_attendance = Attendance.query.filter_by(date=datetime.now().date(),
                                                       attendance_status='present').count()
    elif current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            total_employees = Employee.query.filter_by(is_active=True,
                                                       company_id=supervisor_employee.company_id).count()
            total_companies = 1
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


@reports_bp.route('/reports/attendance')
@login_required
def attendance_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id', type=int)
    attendance_type = request.args.get('attendance_type', 'all')
    show_all = request.args.get('show_all', 'false')

    query = Attendance.query

    if start_date:
        query = query.filter(Attendance.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Attendance.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    if attendance_type and attendance_type != 'all':
        query = query.filter(Attendance.attendance_type == attendance_type)

    if not start_date and not end_date and show_all != 'true':
        last_date = db.session.query(db.func.max(Attendance.date)).scalar()
        if last_date:
            query = query.filter(Attendance.date == last_date)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    paginated_attendances = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=per_page,
                                                                             error_out=False)

    employees = Employee.query.filter_by(is_active=True).all()

    last_prep_date = db.session.query(db.func.max(Attendance.date)).scalar()

    total_count = query.count()
    individual_count = query.filter(Attendance.attendance_type == 'individual').count()
    group_count = query.filter(Attendance.attendance_type == 'group').count()
    present_count = query.filter(Attendance.attendance_status == 'present').count()
    late_count = query.filter(Attendance.attendance_status == 'late').count()
    absent_count = query.filter(Attendance.attendance_status == 'absent').count()
    unique_days = query.with_entities(Attendance.date).distinct().count()

    return render_template('reports/attendance_report.html',
                           attendances=paginated_attendances.items,
                           employees=employees,
                           pagination=paginated_attendances,
                           total_count=total_count,
                           individual_count=individual_count,
                           group_count=group_count,
                           present_count=present_count,
                           late_count=late_count,
                           absent_count=absent_count,
                           unique_days=unique_days,
                           last_prep_date=last_prep_date,
                           start_date=start_date,
                           end_date=end_date,
                           selected_employee=employee_id,
                           selected_type=attendance_type,
                           show_all=show_all,
                           per_page=per_page,
                           now=datetime.now())


@reports_bp.route('/reports/financial')
@login_required
@role_required('admin', 'finance')
def financial_report():
    month_year = request.args.get('month_year', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    available_months = db.session.query(Salary.month_year).distinct().order_by(Salary.month_year.desc()).all()
    available_months = [m[0] for m in available_months if m[0]]

    if 'all' not in available_months:
        available_months.insert(0, 'all')

    report = None

    if month_year == 'all' or not month_year:
        paginated_salaries = Salary.query.order_by(Salary.month_year.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        salaries = paginated_salaries.items

        if salaries:
            salaries_data = []
            for salary in salaries:
                period_display = _format_period_display(salary)

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
                    'is_paid': salary.is_paid,
                    'basic_salary': salary.basic_salary_amount,
                    'resident_allowance': salary.resident_allowance_amount,
                    'clothing': salary.clothing_allowance_amount,
                    'health_card': salary.health_card_amount,
                    'insurance': salary.insurance_amount
                })

            stats_query = Salary.query
            total_employees = stats_query.count()
            total_attendance_days = db.session.query(func.sum(Salary.attendance_days)).scalar() or 0
            total_salaries = db.session.query(func.sum(Salary.total_salary)).scalar() or 0
            paid_salaries = stats_query.filter(Salary.is_paid == True).count()

            report = {
                'month_year': 'جميع الأشهر',
                'start_date': None,
                'end_date': None,
                'total_employees': total_employees,
                'total_attendance_days': total_attendance_days,
                'total_salaries': float(total_salaries),
                'paid_salaries': paid_salaries,
                'salaries': salaries_data
            }

    elif month_year and month_year != 'all':
        try:
            query = Salary.query.filter(Salary.month_year == month_year)

            if query.count() == 0 and '-' in month_year:
                parts = month_year.split('-')
                if len(parts[0]) == 4:
                    alt_format = f"{parts[1]}-{parts[0]}"
                else:
                    alt_format = f"{parts[1]}-{parts[0]}"
                query = Salary.query.filter(Salary.month_year == alt_format)

            paginated_salaries = query.order_by(Salary.employee_id).paginate(
                page=page, per_page=per_page, error_out=False
            )
            salaries = paginated_salaries.items

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
                        'is_paid': salary.is_paid,
                        'basic_salary': salary.basic_salary_amount,
                        'resident_allowance': salary.resident_allowance_amount,
                        'clothing': salary.clothing_allowance_amount,
                        'health_card': salary.health_card_amount,
                        'insurance': salary.insurance_amount
                    })

                total_employees = query.count()
                total_attendance_days = db.session.query(func.sum(Salary.attendance_days)).filter(
                    Salary.month_year == month_year).scalar() or 0
                total_salaries = db.session.query(func.sum(Salary.total_salary)).filter(
                    Salary.month_year == month_year).scalar() or 0
                paid_salaries = query.filter(Salary.is_paid == True).count()

                report = {
                    'month_year': month_year,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_employees': total_employees,
                    'total_attendance_days': total_attendance_days,
                    'total_salaries': float(total_salaries),
                    'paid_salaries': paid_salaries,
                    'salaries': salaries_data
                }
        except Exception as e:
            flash(f'خطأ في معالجة الشهر: {str(e)}', 'danger')

    return render_template('reports/financial_report.html',
                           report=report,
                           available_months=available_months,
                           selected_month=month_year,
                           pagination=paginated_salaries if 'paginated_salaries' in dir() else None,
                           page=page,
                           per_page=per_page,
                           now=datetime.now())


@reports_bp.route('/reports/employees')
@login_required
def employees_report():
    employees = Employee.query.all()
    return render_template('reports/employees_report.html', employees=employees)


@reports_bp.route('/reports/regions')
@login_required
def regions_report():
    from sqlalchemy import func

    regions_result = db.session.query(
        Employee.region,
        db.func.count(Employee.id).label('count')
    ).filter(
        Employee.is_active == True,
        Employee.region != None,
        Employee.region != ''
    ).group_by(Employee.region).all()

    regions_data = []
    total_employees = 0

    for row in regions_result:
        region_name = row[0]
        employees_count = row[1]

        total_employees += employees_count

        companies_count = db.session.query(Employee.company_id).filter(
            Employee.region == region_name,
            Employee.is_active == True
        ).distinct().count()

        regions_data.append({
            'region': region_name,
            'companies_count': companies_count,
            'employees_count': employees_count
        })

    regions_data.sort(key=lambda x: x['employees_count'], reverse=True)

    return render_template('reports/regions_report.html',
                           regions_data=regions_data,
                           total_employees=total_employees,
                           now=datetime.now())


@reports_bp.route('/reports/monthly_close', methods=['GET', 'POST'])
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


@reports_bp.route('/reports/financial_monthly')
@login_required
@role_required('admin', 'finance')
def financial_monthly_report():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

    month_name = start_date.strftime('%B %Y')
    month_year_formats = [
        start_date.strftime('%Y-%m'),
        start_date.strftime('%m-%Y')
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

    invoices_paid = Invoice.query.filter(
        Invoice.paid_date >= start_date,
        Invoice.paid_date <= end_date,
        Invoice.is_paid == True
    ).all()

    invoices_paid_total = sum(i.amount for i in invoices_paid)

    invoices_due = Invoice.query.filter(
        Invoice.due_date >= start_date,
        Invoice.due_date <= end_date,
        Invoice.is_paid == False
    ).all()

    invoices_due_total = sum(i.amount for i in invoices_due)

    expenses = FinancialTransaction.query.filter(
        FinancialTransaction.transaction_type.in_(['deduction', 'penalty']),
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).all()
    expenses_total = sum(e.amount for e in expenses) if expenses else 0

    advances = FinancialTransaction.query.filter(
        FinancialTransaction.transaction_type == 'advance',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).all()
    advances_total = sum(a.amount for a in advances)

    overtime = FinancialTransaction.query.filter(
        FinancialTransaction.transaction_type == 'overtime',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    ).all()
    overtime_total = sum(o.amount for o in overtime)

    total_expenses = salaries_total + expenses_total + advances_total

    total_income = contracts_total + invoices_paid_total

    profit = total_income - total_expenses

    companies_data = []
    for company in Company.query.all():
        company_contracts = Contract.query.filter_by(company_id=company.id).all()
        company_contracts_value = 0
        for c in company_contracts:
            if c.contract_type == 'monthly':
                company_contracts_value += c.contract_value
            else:
                company_contracts_value += c.contract_value / 12

        company_invoices = db.session.query(func.sum(Invoice.amount)).filter(
            Invoice.paid_date >= start_date,
            Invoice.paid_date <= end_date,
            Invoice.is_paid == True
        ).join(Contract).filter(Contract.company_id == company.id).scalar() or 0

        company_total_income = company_contracts_value + company_invoices

        company_salaries = 0

        for fmt in month_year_formats:
            value = db.session.query(func.sum(Salary.total_salary)).filter(
                Salary.month_year == fmt,
                Salary.is_paid == True
            ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

            if value > 0:
                company_salaries = value
                break

        company_advances = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.transaction_type == 'advance',
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

        company_overtime = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.transaction_type == 'overtime',
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        ).join(Employee).filter(Employee.company_id == company.id).scalar() or 0

        company_total_expenses = company_salaries + (company_advances or 0) + (company_overtime or 0)

        company_net = company_total_income - company_total_expenses

        companies_data.append({
            'name': company.name,
            'contracts_value': company_contracts_value,
            'invoices_value': company_invoices,
            'total_income': company_total_income,
            'salaries': company_salaries,
            'advances': company_advances or 0,
            'overtime': company_overtime or 0,
            'total_expenses': company_total_expenses,
            'net': company_net
        })

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


@reports_bp.route('/reports/evaluations_analysis')
@login_required
def evaluations_analysis_report():
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

    total_evaluations = len(evaluations)
    avg_score = sum(e.score for e in evaluations) / total_evaluations if total_evaluations > 0 else 0

    excellent = len([e for e in evaluations if e.score >= 90])
    very_good = len([e for e in evaluations if 75 <= e.score < 90])
    good = len([e for e in evaluations if 60 <= e.score < 75])
    fair = len([e for e in evaluations if 50 <= e.score < 60])
    poor = len([e for e in evaluations if e.score < 50])

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

    criteria_scores = {}
    for e in evaluations:
        pass

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


@reports_bp.route('/reports/evaluations_by_location')
@login_required
def evaluations_by_location_report():
    location_id = request.args.get('location_id', type=int)

    query = Evaluation.query.filter(Evaluation.evaluation_type == 'supervisor')

    if location_id:
        query = query.filter(Evaluation.location_id == location_id)

    evaluations = query.order_by(Evaluation.date.desc()).all()

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

    return render_template('reports/evaluations_by_location.html',
                           evaluations=evaluations,
                           locations=locations,
                           location_stats=location_stats,
                           selected_location=location_id,
                           now=datetime.now())


@reports_bp.route('/reports/evaluations_by_region')
@login_required
def evaluations_by_region_report():
    region_id = request.args.get('region_id', type=int)

    query = Evaluation.query.filter(Evaluation.evaluation_type == 'supervisor')

    if region_id:
        query = query.filter(Evaluation.region_id == region_id)

    evaluations = query.order_by(Evaluation.date.desc()).all()

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

    region_stats.sort(key=lambda x: x['count'], reverse=True)

    return render_template('reports/evaluations_by_region.html',
                           evaluations=evaluations,
                           regions=regions,
                           region_stats=region_stats,
                           selected_region=region_id,
                           now=datetime.now())


@reports_bp.route('/reports/evaluations_by_region/pdf')
@login_required
def export_evaluations_by_region_pdf():
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

    region_stats.sort(key=lambda x: x['count'], reverse=True)

    total_evaluations = len(evaluations)
    total_employees = len(set([e.employee_id for e in evaluations]))
    overall_avg = sum(e.score for e in evaluations) / total_evaluations if total_evaluations > 0 else 0

    html_content = render_template('reports/pdf/evaluations_by_region_pdf.html',
                                   region_stats=region_stats,
                                   total_evaluations=total_evaluations,
                                   total_employees=total_employees,
                                   overall_avg=round(overall_avg, 1),
                                   now=datetime.now(),
                                   current_user=current_user)

    if HTML is None:
        return 'PDF not available - weasyprint not installed', 503
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=evaluations_by_region_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return response


@reports_bp.route('/reports/evaluations_by_location/pdf')
@login_required
def export_evaluations_by_location_pdf():
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

    if HTML is None:
        return 'PDF not available - weasyprint not installed', 503
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=evaluations_by_location_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return response


@reports_bp.route('/reports/attendance/pdf')
@login_required
def export_attendance_pdf():
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

    if HTML is None:
        return 'PDF not available - weasyprint not installed', 503
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return response


@reports_bp.route('/reports/financial/pdf')
@login_required
def export_financial_pdf():
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

    if HTML is None:
        return 'PDF not available - weasyprint not installed', 503
    pdf = HTML(string=html_content).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers[
        'Content-Disposition'] = f'attachment; filename=financial_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

    return response


@reports_bp.route('/reports/attendance/export')
@login_required
def export_attendance_excel():
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

    data = []
    for att in attendances:
        data.append({
            'التاريخ': att.date.strftime('%Y-%m-%d'),
            'الموظف': att.employee.name if att.employee else '',
            'الحالة': att.get_status_display(),
            'دقائق التأخير': att.late_minutes or 0
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='الحضور', index=False)

    output.seek(0)
    filename = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@reports_bp.route('/reports/salaries/export')
@login_required
@role_required('admin', 'finance')
def export_salaries_excel():
    period_key = request.args.get('period_key', '')

    query = Salary.query
    if period_key:
        query = query.filter(Salary.month_year == period_key)

    salaries = query.all()

    data = []
    for salary in salaries:
        data.append({
            'الموظف': salary.employee.name if salary.employee else '',
            'الشركة': salary.employee.company.name if salary.employee and salary.employee.company else '',
            'الفترة': _format_period_display(salary),
            'أيام الحضور': salary.attendance_days,
            'صافي الراتب': salary.total_salary or 0,
            'الحالة': 'مدفوع' if salary.is_paid else 'غير مدفوع'
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='الرواتب', index=False)

    output.seek(0)
    filename = f"salaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, download_name=filename, as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
