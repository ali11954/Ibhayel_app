from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from models import (
    db, Employee, Company, Salary, AttendancePeriodTransfer, Contract, Invoice,
    Account, JournalEntry, JournalEntryDetail, LaborMonthlyCost, ContractorAnnualCost
)
from utils import role_required, get_next_entry_number, get_financial_month_dates

labor_bp = Blueprint('labor_bp', __name__)


def calculate_worker_monthly_cost(employee, attendance_days, month_year):
    daily_rate = employee.basic_salary / 30
    basic_salary = daily_rate * attendance_days

    resident_allowance = 0
    if employee.is_resident:
        resident_allowance = 500 * attendance_days

    insurance = employee.monthly_insurance

    monthly_clothing = employee.clothing_allowance / 12

    monthly_health = employee.health_card_allowance / 12

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

        cost = calculate_worker_monthly_cost(employee, attendance_days, month_year)

        results.append(cost)

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
    from models import Account, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from utils import get_next_entry_number

    summary = cost_summary['summary']

    basic_salary_expense = Account.query.filter_by(code='511001').first()
    resident_allowance_expense = Account.query.filter_by(code='511002').first()
    insurance_expense = Account.query.filter_by(code='511003').first()
    clothing_expense = Account.query.filter_by(code='511004').first()
    health_expense = Account.query.filter_by(code='511005').first()

    salaries_payable = Account.query.filter_by(code='211001').first()
    allowances_payable = Account.query.filter_by(code='211002').first()
    insurance_payable = Account.query.filter_by(code='211003').first()

    from models import create_labor_accounts
    if not all([basic_salary_expense, resident_allowance_expense, insurance_expense,
                clothing_expense, health_expense, salaries_payable, allowances_payable, insurance_payable]):
        create_labor_accounts()
        basic_salary_expense = Account.query.filter_by(code='511001').first()
        resident_allowance_expense = Account.query.filter_by(code='511002').first()
        insurance_expense = Account.query.filter_by(code='511003').first()
        clothing_expense = Account.query.filter_by(code='511004').first()
        health_expense = Account.query.filter_by(code='511005').first()
        salaries_payable = Account.query.filter_by(code='211001').first()
        allowances_payable = Account.query.filter_by(code='211002').first()
        insurance_payable = Account.query.filter_by(code='211003').first()

    entry_number = get_next_entry_number()

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


@labor_bp.route('/labor/costs/calculate', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def calculate_labor_costs():
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

        attendance_data = {}
        for detail in transfer.transfers_details:
            if detail.employee and detail.employee.employee_type == 'worker':
                attendance_data[detail.employee_id] = detail.attendance_days

        if not attendance_data:
            flash('⚠️ لا يوجد عمال في فترة الترحيل هذه', 'warning')
            return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

        result = calculate_all_workers_monthly_cost(
            company_id=transfer.company_id,
            attendance_data=attendance_data,
            month_year=month_year or transfer.period_name
        )

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


@labor_bp.route('/labor/costs/journal/<int:transfer_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def create_labor_costs_journal(transfer_id):
    import json

    try:
        transfer = AttendancePeriodTransfer.query.get(transfer_id)
        if not transfer:
            flash('⚠️ فترة الترحيل غير موجودة', 'danger')
            return redirect(url_for('period_transfer_list'))

        result = session.get('labor_cost_result')
        if not result or result.get('company_id') != transfer.company_id:
            attendance_data = {}
            for detail in transfer.transfers_details:
                if detail.employee and detail.employee.employee_type == 'worker':
                    attendance_data[detail.employee_id] = detail.attendance_days

            result = calculate_all_workers_monthly_cost(
                company_id=transfer.company_id,
                attendance_data=attendance_data,
                month_year=transfer.period_name
            )

        existing = JournalEntry.query.filter(
            JournalEntry.reference_type == 'worker_salaries',
            JournalEntry.description.like(f'%{transfer.period_name}%')
        ).first()

        if existing:
            flash(f'⚠️ يوجد قيد محاسبي مسبق لهذه الفترة: {existing.entry_number}', 'warning')
            return redirect(url_for('view_period_transfer', transfer_id=transfer.id))

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


@labor_bp.route('/labor/costs/report')
@login_required
@role_required('admin', 'finance')
def labor_costs_report():
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


@labor_bp.route('/labor/costs/view/<int:transfer_id>')
@login_required
@role_required('admin', 'finance')
def view_labor_costs(transfer_id):
    from models import AttendancePeriodTransfer

    transfer = AttendancePeriodTransfer.query.get_or_404(transfer_id)

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


@labor_bp.route('/labor/contractor/annual')
@login_required
@role_required('admin', 'finance')
def contractor_annual_costs():
    from models import ContractorAnnualCost

    year = request.args.get('year', type=int)
    if not year:
        year = datetime.now().year

    costs = ContractorAnnualCost.query.filter_by(year=year).all()

    total_tax = sum(c.tax_amount for c in costs)
    total_zakat = sum(c.zakat_amount for c in costs)

    return render_template('labor/contractor_costs.html',
                           costs=costs,
                           year=year,
                           total_tax=total_tax,
                           total_zakat=total_zakat,
                           now=datetime.now())


@labor_bp.route('/labor/contractor/journal/<int:year>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def create_contractor_journal(year):
    from models import Account, JournalEntry, JournalEntryDetail, ContractorAnnualCost, db
    from utils import get_next_entry_number
    from datetime import datetime

    try:
        company_id = request.form.get('company_id', type=int)

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

        existing = JournalEntry.query.filter(
            JournalEntry.reference_type == 'contractor_annual',
            JournalEntry.reference_id == annual_cost.id
        ).first()

        if existing:
            flash(f'⚠️ يوجد قيد محاسبي مسبق لهذه السنة: {existing.entry_number}', 'warning')
            return redirect(url_for('contractor_annual_costs', year=year))

        tax_expense = Account.query.filter_by(code='521001').first()
        zakat_expense = Account.query.filter_by(code='521002').first()
        tax_payable = Account.query.filter_by(code='221001').first()
        zakat_payable = Account.query.filter_by(code='221002').first()

        from models import create_labor_accounts
        if not all([tax_expense, zakat_expense, tax_payable, zakat_payable]):
            create_labor_accounts()
            tax_expense = Account.query.filter_by(code='521001').first()
            zakat_expense = Account.query.filter_by(code='521002').first()
            tax_payable = Account.query.filter_by(code='221001').first()
            zakat_payable = Account.query.filter_by(code='221002').first()

        entry_number = get_next_entry_number()

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
