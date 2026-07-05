from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, make_response, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models import (
    db, Employee, FinancialTransaction, Salary, Company, Contract, Invoice,
    AttendancePeriodTransfer, AttendancePreparation, MealDeduction, MealDeductionSetting,
    Account, JournalEntry, JournalEntryDetail
)
from utils import (
    role_required, create_salary_journal_entry, create_transaction_journal_entry,
    create_invoice_journal_entry, create_invoice_payment_journal_entry,
    reverse_journal_entry, reverse_invoice_journal_entry, get_next_entry_number,
    create_journal_entry
)
import time
import traceback
import pandas as pd
from io import BytesIO

financial_bp = Blueprint('financial', __name__)


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


@financial_bp.route('/invoices/partial_payments/<int:invoice_id>')
@login_required
def invoice_partial_payments(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('contracts/invoice_payments.html', invoice=invoice)


@financial_bp.route('/financial/salaries')
@login_required
@role_required('admin', 'finance', 'supervisor')
def salaries_list():
    from collections import defaultdict
    from sqlalchemy.orm import joinedload

    db.session.expire_all()

    period_key = request.args.get('period_key', '')
    status_filter = request.args.get('status', 'all')
    employee_id = request.args.get('employee_id', type=int)
    company_id = request.args.get('company_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = db.session.query(Salary).options(
        joinedload(Salary.employee)
    )

    if period_key:
        query = query.filter(Salary.month_year == period_key)

    if status_filter == 'paid':
        query = query.filter(Salary.is_paid == True)
    elif status_filter == 'unpaid':
        query = query.filter(Salary.is_paid == False)

    if employee_id:
        query = query.filter(Salary.employee_id == employee_id)

    if company_id:
        query = query.join(Salary.employee).filter(Employee.company_id == company_id)

    if current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            worker_ids = [e.id for e in
                          Employee.query.filter_by(supervisor_id=supervisor_employee.id, is_active=True).all()]
            query = query.filter(Salary.employee_id.in_(worker_ids))
        else:
            query = query.filter(False)

    paginated_salaries = query.order_by(Salary.month_year.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    all_salaries = paginated_salaries.items

    companies_dict = defaultdict(lambda: {
        'name': '',
        'salaries': [],
        'total_amount': 0.0,
        'paid_count': 0,
        'unpaid_count': 0
    })

    for salary in all_salaries:
        if salary.employee and salary.employee.company_id:
            company = db.session.get(Company, salary.employee.company_id)
            company_id_val = company.id if company else 0
            company_name = company.name if company else 'الشركة الأم'
        else:
            company_id_val = 0
            company_name = 'الشركة الأم'

        companies_dict[company_id_val]['name'] = company_name
        companies_dict[company_id_val]['salaries'].append(salary)
        companies_dict[company_id_val]['total_amount'] += float(salary.total_salary or 0)

        if salary.is_paid:
            companies_dict[company_id_val]['paid_count'] += 1
        else:
            companies_dict[company_id_val]['unpaid_count'] += 1

    companies_dict = dict(companies_dict)

    available_periods = []
    all_periods = db.session.query(Salary.month_year, Salary.notes).distinct().order_by(
        Salary.month_year.desc()).all()
    for period in all_periods:
        display = period[1] if period[1] and 'فترة من' in period[1] else period[0]
        available_periods.append({'key': period[0], 'display': display})

    stats_query = db.session.query(Salary)
    if period_key:
        stats_query = stats_query.filter(Salary.month_year == period_key)
    if company_id:
        stats_query = stats_query.join(Salary.employee).filter(Employee.company_id == company_id)

    stats = {
        'total': paginated_salaries.total,
        'paid': stats_query.filter(Salary.is_paid == True).count(),
        'unpaid': stats_query.filter(Salary.is_paid == False).count(),
        'total_amount': float(
            stats_query.with_entities(func.coalesce(func.sum(Salary.total_salary), 0)).scalar() or 0),
        'paid_amount': float(stats_query.filter(Salary.is_paid == True).with_entities(
            func.coalesce(func.sum(Salary.total_salary), 0)).scalar() or 0),
        'unpaid_amount': float(stats_query.filter(Salary.is_paid == False).with_entities(
            func.coalesce(func.sum(Salary.total_salary), 0)).scalar() or 0),
        'zero_or_negative': stats_query.filter(Salary.total_salary <= 0).count()
    }

    employees = db.session.query(Employee.id, Employee.name, Employee.job_title, Employee.company_id).filter(
        Employee.is_active == True
    ).all()
    employees_list = [{'id': e[0], 'name': e[1], 'job_title': e[2], 'company_id': e[3]} for e in employees]

    companies = db.session.query(Company).all()

    current_params = ''
    if period_key:
        current_params += f'&period_key={period_key}'
    if status_filter != 'all':
        current_params += f'&status={status_filter}'
    if employee_id:
        current_params += f'&employee_id={employee_id}'
    if company_id:
        current_params += f'&company_id={company_id}'

    response = make_response(render_template('financial/salaries.html',
                                             salaries=all_salaries,
                                             companies_dict=companies_dict,
                                             companies=companies,
                                             available_periods=available_periods,
                                             stats=stats,
                                             employees=employees_list,
                                             selected_period=period_key,
                                             selected_status=status_filter,
                                             selected_employee=employee_id,
                                             selected_company=company_id,
                                             start_date=request.args.get('start_date', ''),
                                             end_date=request.args.get('end_date', ''),
                                             pagination=paginated_salaries,
                                             current_params=current_params,
                                             now=datetime.now()))

    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@financial_bp.route('/financial/salary_calculation', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def salary_calculation():
    from decimal import Decimal, getcontext

    getcontext().prec = 28

    if request.method == 'POST':
        token_key = f'salary_calc_token_{current_user.id}'
        last_run = session.get(token_key, 0)
        if time.time() - last_run < 5:
            flash('⚠️ يتم معالجة الطلب بالفعل، يرجى الانتظار', 'warning')
            return redirect(url_for('financial.salary_calculation'))
        session[token_key] = time.time()

        transfer_id = request.form.get('transfer_id')
        if not transfer_id:
            flash('⚠️ الرجاء اختيار فترة ترحيل أولاً', 'danger')
            return redirect(url_for('financial.salary_calculation'))

        transfer = db.session.get(AttendancePeriodTransfer, int(transfer_id))

        if not transfer:
            flash('⚠️ فترة الترحيل غير موجودة', 'danger')
            return redirect(url_for('financial.salary_calculation'))
        if transfer.is_transferred:
            flash(f'⚠️ فترة الترحيل "{transfer.period_name}" تم ترحيلها مسبقاً', 'warning')
            return redirect(url_for('financial.salary_calculation'))
        if not transfer.transfers_details:
            flash('⚠️ لا توجد بيانات في فترة الترحيل المحددة', 'danger')
            return redirect(url_for('financial.salary_calculation'))

        try:
            start_date = transfer.start_date
            end_date = transfer.end_date
            period_name = transfer.period_name
            count = 0
            total_salaries = 0
            failed_employees = []

            for detail in transfer.transfers_details:
                try:
                    employee = db.session.get(Employee, detail.employee_id)

                    if not employee:
                        print(f"⚠️ موظف غير موجود للمعرف {detail.employee_id}")
                        failed_employees.append({
                            'employee': f'ID: {detail.employee_id}',
                            'error': 'الموظف غير موجود'
                        })
                        continue

                    attendance_days = max(0, min(detail.attendance_days, 31))
                    period_key = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

                    breakdown = employee.calculate_salary_breakdown(
                        attendance_days=attendance_days,
                        paid_leave_days=0,
                        start_date=start_date,
                        end_date=end_date
                    )

                    if breakdown.get('cash_payout', 0) <= 0 and attendance_days > 0:
                        print(
                            f"⚠️ {employee.name}: cash_payout={breakdown.get('cash_payout')} رغم حضور {attendance_days} أيام")

                    salary = Salary.query.filter_by(
                        employee_id=employee.id,
                        month_year=period_key
                    ).first()

                    if not salary:
                        salary = Salary(
                            employee_id=employee.id,
                            month_year=period_key,
                            base_salary=employee.salary,
                            notes=f"فترة من {start_date} إلى {end_date}",
                            attendance_days=attendance_days
                        )
                        db.session.add(salary)
                        db.session.flush()

                    salary.basic_salary_amount = breakdown.get('basic_payout', 0)
                    salary.resident_allowance_amount = breakdown.get('resident_allowance', 0)
                    salary.clothing_allowance_amount = breakdown.get('clothing_allowance', 0)
                    salary.health_card_amount = breakdown.get('health_card', 0)
                    salary.insurance_amount = breakdown.get('insurance', 0)
                    salary.contractor_profit = breakdown.get('contractor_profit', 0)
                    salary.total_salary = breakdown.get('cash_payout', 0)

                    total_salaries += salary.total_salary

                    if salary.total_salary > 0:
                        db.session.query(FinancialTransaction).filter(
                            FinancialTransaction.employee_id == employee.id,
                            FinancialTransaction.is_settled == False,
                            FinancialTransaction.date >= start_date,
                            FinancialTransaction.date <= end_date
                        ).update({
                            FinancialTransaction.is_settled: True,
                            FinancialTransaction.settled_date: end_date
                        }, synchronize_session=False)

                    detail.is_processed = True
                    count += 1

                    print(
                        f"✅ {employee.name}: basic={salary.basic_salary_amount:.0f}, total={salary.total_salary:.0f}")

                except Exception as emp_error:
                    print(f"❌ خطأ في معالجة {detail.employee.name if detail.employee else 'موظف'}: {emp_error}")
                    failed_employees.append({
                        'employee': detail.employee.name if detail.employee else f'ID: {detail.employee_id}',
                        'error': str(emp_error)
                    })
                    continue

            transfer.is_transferred = True
            transfer.transfer_date = datetime.now().date()
            db.session.commit()

            flash(f'✅ تم حساب وترحيل رواتب {count} موظف من فترة "{period_name}"', 'success')
            flash(f'💰 إجمالي الرواتب: {total_salaries:,.2f} ريال', 'info')

            if failed_employees:
                flash(f'⚠️ فشل حساب {len(failed_employees)} موظف', 'warning')

            return redirect(url_for('financial.salaries_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')
            print(f"❌ خطأ: {e}")
            traceback.print_exc()
            return redirect(url_for('financial.salary_calculation'))

    pending_transfers = AttendancePeriodTransfer.query.filter_by(is_transferred=False).order_by(
        AttendancePeriodTransfer.start_date.desc()).all()
    completed_transfers = AttendancePeriodTransfer.query.filter_by(is_transferred=True).order_by(
        AttendancePeriodTransfer.start_date.desc()).limit(10).all()
    return render_template('financial/salary_calculation.html',
                           pending_transfers=pending_transfers,
                           completed_transfers=completed_transfers)


@financial_bp.route('/financial/salaries/pay/<int:salary_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def pay_salary(salary_id):
    salary = Salary.query.get_or_404(salary_id)

    accrual_entry = JournalEntry.query.filter(
        JournalEntry.reference_type == 'salary',
        JournalEntry.reference_id == salary.id
    ).first()

    if not accrual_entry:
        flash('⚠️ لا يوجد قيد استحقاق للراتب. جاري إنشاؤه تلقائياً...', 'info')
        try:
            accrual_entry = create_salary_journal_entry(salary)
            flash(f'✅ تم إنشاء قيد استحقاق الراتب: {accrual_entry.entry_number}', 'success')
        except Exception as e:
            flash(f'❌ حدث خطأ في إنشاء استحقاق الراتب: {str(e)}', 'danger')
            return redirect(url_for('financial.salaries_list'))

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

    if salary.is_paid:
        flash('⚠️ هذا الراتب تم صرفه مسبقاً', 'warning')
        return redirect(url_for('financial.salaries_list'))

    if salary.total_salary <= 0:
        flash('⚠️ لا يمكن صرف راتب بقيمة صفر أو أقل', 'danger')
        return redirect(url_for('financial.salaries_list'))

    try:
        payment_method = request.form.get('payment_method', 'cash')
        payment_reference = request.form.get('payment_reference', '')
        notes = request.form.get('notes', '')

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

            current_balance = payment_account.get_balance()
            if current_balance < salary.total_salary:
                flash(f'⚠️ رصيد البنك غير كافٍ! المتوفر: {current_balance:,.2f} ريال', 'danger')
                return redirect(url_for('financial.pay_salary', salary_id=salary_id))
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

            current_balance = payment_account.get_balance()
            if current_balance < salary.total_salary:
                flash(f'⚠️ رصيد الصندوق غير كافٍ! المتوفر: {current_balance:,.2f} ريال', 'danger')
                flash('💡 يمكنك إيداع نقدي في الصندوق أولاً أو استخدام التحويل البنكي', 'warning')
                return redirect(url_for('financial.pay_salary', salary_id=salary_id))

        salary.is_paid = True
        salary.paid_date = datetime.now().date()
        salary.payment_method = payment_method
        salary.payment_reference = payment_reference
        if notes:
            salary.notes = (salary.notes or '') + f'\nملاحظات الصرف: {notes}'

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

        detail1 = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=salaries_payable.id,
            debit=salary.total_salary,
            credit=0,
            description=f'صرف راتب {salary.employee.name}'
        )
        db.session.add(detail1)

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
        traceback.print_exc()

    return redirect(url_for('financial.salaries_list'))


@financial_bp.route('/financial/salaries/bulk_pay', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def bulk_pay_salaries():
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


@financial_bp.route('/financial/transactions')
@login_required
@role_required('admin', 'finance', 'supervisor')
def transactions_list():
    transaction_type = request.args.get('type', 'all')
    employee_id = request.args.get('employee_id', type=int)
    transferred_filter = request.args.get('transferred', 'all')

    query = FinancialTransaction.query

    if transaction_type != 'all':
        query = query.filter_by(transaction_type=transaction_type)

    if transferred_filter == 'transferred':
        query = query.filter_by(is_settled=True)
    elif transferred_filter == 'not_transferred':
        query = query.filter_by(is_settled=False)

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

    transactions = query.order_by(FinancialTransaction.date.desc()).all()
    employees = Employee.query.filter_by(is_active=True).all()

    stats = {
        'total_count': FinancialTransaction.query.count(),
        'total_amount': db.session.query(func.sum(FinancialTransaction.amount)).scalar() or 0,
        'pending_count': FinancialTransaction.query.filter_by(is_settled=False).count(),
        'pending_amount': db.session.query(func.sum(FinancialTransaction.amount)).filter_by(
            is_settled=False).scalar() or 0,
        'transferred_count': FinancialTransaction.query.filter_by(is_settled=True).count(),
        'transferred_amount': db.session.query(func.sum(FinancialTransaction.amount)).filter_by(
            is_settled=True).scalar() or 0
    }

    return render_template('financial/transactions.html',
                           transactions=transactions,
                           employees=employees,
                           selected_type=transaction_type,
                           selected_employee=employee_id,
                           selected_transferred=transferred_filter,
                           stats=stats,
                           now=datetime.now())


@financial_bp.route('/financial/add_transaction', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def add_transaction():
    if request.method == 'POST':
        try:
            employee_id = request.form.get('employee_id')
            transaction_type = request.form.get('transaction_type')
            amount = float(request.form.get('amount'))
            description = request.form.get('description')
            transaction_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

            if amount <= 0:
                flash('⚠️ المبلغ يجب أن يكون أكبر من صفر', 'danger')
                return redirect(url_for('financial.add_transaction'))

            transaction = FinancialTransaction(
                employee_id=employee_id,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                date=transaction_date,
                created_by=current_user.id,
                is_settled=False,
                journal_entry_id=None
            )
            db.session.add(transaction)
            db.session.commit()

            type_names = {
                'advance': 'السلفة',
                'overtime': 'الإضافي',
                'deduction': 'الخصم',
                'penalty': 'الجزاء',
                'cafeteria': 'خصم البوفية',
                'restaurant': 'خصم المطعم',
                'meal': 'خصم الوجبات'
            }
            type_name = type_names.get(transaction_type, transaction_type)

            flash(
                f'✅ تم إضافة {type_name} بقيمة {amount:,.0f} ريال بنجاح (لم يتم ترحيلها إلى القيود المحاسبية بعد)',
                'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('financial.add_transaction'))

        return redirect(url_for('financial.transactions_list'))

    employees = Employee.query.filter_by(is_active=True).all()

    transaction_types = {
        'advance': 'سلفة',
        'overtime': 'إضافي',
        'deduction': 'خصم',
        'penalty': 'جزاء',
        'cafeteria': 'خصم بوفية',
        'restaurant': 'خصم مطعم',
        'meal': 'خصم وجبات'
    }

    return render_template('financial/add_transaction.html',
                           employees=employees,
                           transaction_types=transaction_types,
                           now=datetime.now())


@financial_bp.route('/financial/delete_transaction/<int:trans_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def delete_transaction(trans_id):
    transaction = FinancialTransaction.query.get_or_404(trans_id)

    if transaction.is_settled:
        flash('⚠️ لا يمكن حذف المعاملة لأنها تم ترحيلها بالفعل', 'danger')
        return redirect(url_for('financial.transactions_list'))

    if transaction.journal_entry_id:
        flash('⚠️ لا يمكن حذف المعاملة لأن لها قيد محاسبي مرتبط', 'danger')
        return redirect(url_for('financial.transactions_list'))

    try:
        type_names = {
            'advance': 'السلفة',
            'overtime': 'الإضافي',
            'deduction': 'الخصم',
            'penalty': 'الجزاء',
            'cafeteria': 'خصم البوفية',
            'restaurant': 'خصم المطعم',
            'meal': 'خصم الوجبات'
        }
        type_name = type_names.get(transaction.transaction_type, transaction.transaction_type)

        db.session.delete(transaction)
        db.session.commit()
        flash(f'✅ تم حذف {type_name} بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('financial.transactions_list'))


@financial_bp.route('/financial/bulk_transfer', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def bulk_transfer_transactions():
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({'success': False, 'error': 'لم يتم تحديد أي معاملات'})

        count = 0
        total_amount = 0
        transactions = FinancialTransaction.query.filter(
            FinancialTransaction.id.in_(transaction_ids),
            FinancialTransaction.is_settled == False
        ).all()

        for transaction in transactions:
            transaction.is_settled = True
            transaction.settled_date = datetime.now().date()
            count += 1
            total_amount += transaction.amount

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'✅ تم ترحيل {count} معاملة بقيمة إجمالية {total_amount:,.0f} ريال',
            'count': count,
            'total': total_amount
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@financial_bp.route('/financial/transaction/<int:trans_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def edit_transaction(trans_id):
    transaction = FinancialTransaction.query.get_or_404(trans_id)

    if transaction.is_settled:
        flash('⚠️ لا يمكن تعديل معاملة تم ترحيلها بالفعل', 'danger')
        return redirect(url_for('financial.transactions_list'))

    if request.method == 'POST':
        try:
            transaction.transaction_type = request.form.get('transaction_type')
            transaction.amount = float(request.form.get('amount'))
            transaction.description = request.form.get('description')
            transaction.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

            db.session.commit()
            flash('✅ تم تحديث المعاملة بنجاح', 'success')
            return redirect(url_for('financial.transactions_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    employees = Employee.query.filter_by(is_active=True).all()
    transaction_types = {
        'advance': 'سلفة',
        'overtime': 'إضافي',
        'deduction': 'خصم',
        'penalty': 'جزاء',
        'cafeteria': 'خصم بوفية',
        'restaurant': 'خصم مطعم',
        'meal': 'خصم وجبات'
    }

    return render_template('financial/edit_transaction.html',
                           transaction=transaction,
                           employees=employees,
                           transaction_types=transaction_types,
                           now=datetime.now())


@financial_bp.route('/financial/transactions/report')
@login_required
@role_required('admin', 'finance')
def transactions_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    transaction_type = request.args.get('type', 'all')

    query = FinancialTransaction.query

    if start_date:
        query = query.filter(FinancialTransaction.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(FinancialTransaction.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if transaction_type != 'all':
        query = query.filter_by(transaction_type=transaction_type)

    transactions = query.order_by(FinancialTransaction.date.desc()).all()

    stats = {}
    for t in ['advance', 'overtime', 'deduction', 'penalty', 'cafeteria', 'restaurant', 'meal']:
        stats[t] = {
            'count': len([x for x in transactions if x.transaction_type == t]),
            'amount': sum(x.amount for x in transactions if x.transaction_type == t)
        }

    return render_template('financial/transactions_report.html',
                           transactions=transactions,
                           stats=stats,
                           start_date=start_date,
                           end_date=end_date,
                           selected_type=transaction_type,
                           now=datetime.now())


@financial_bp.route('/financial/reverse_transaction/<int:trans_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def reverse_transaction(trans_id):
    transaction = FinancialTransaction.query.get_or_404(trans_id)

    if not transaction.journal_entry_id:
        flash('⚠️ هذه المعاملة ليس لها قيد محاسبي لعكسه', 'danger')
        return redirect(url_for('financial.transactions_list'))

    if transaction.is_settled:
        flash('⚠️ لا يمكن عكس قيد معاملة تم ترحيلها', 'danger')
        return redirect(url_for('financial.transactions_list'))

    try:
        reverse_entry = reverse_journal_entry(transaction.journal_entry_id)

        db.session.delete(transaction)
        db.session.commit()

        flash(f'✅ تم عكس القيد المحاسبي (رقم: {reverse_entry.entry_number}) وحذف المعاملة بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

    return redirect(url_for('financial.transactions_list'))


@financial_bp.route('/financial/transfer_to_salary', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def transfer_transaction_to_salary():
    try:
        data = request.get_json()

        if not data or 'transaction_id' not in data:
            return jsonify({'success': False, 'error': 'transaction_id مطلوب'}), 400

        transaction_id = data.get('transaction_id')

        transaction = (
            FinancialTransaction.query
            .filter_by(id=transaction_id)
            .with_for_update()
            .first()
        )

        if not transaction:
            return jsonify({'success': False, 'error': 'المعاملة غير موجودة'}), 404

        if transaction.is_settled:
            return jsonify({'success': False, 'error': 'المعاملة تم ترحيلها مسبقاً'}), 400

        if transaction.journal_entry_id:
            return jsonify({'success': False, 'error': 'المعاملة لها قيد محاسبي بالفعل'}), 400

        if not transaction.amount or transaction.amount <= 0:
            return jsonify({'success': False, 'error': 'مبلغ المعاملة غير صالح'}), 400

        journal_entry = create_transaction_journal_entry(transaction)

        if not journal_entry:
            db.session.rollback()
            return jsonify({'success': False, 'error': 'فشل في إنشاء القيد المحاسبي'}), 500

        transaction.is_settled = True
        transaction.settled_date = datetime.utcnow().date()
        transaction.journal_entry_id = journal_entry.id

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم ترحيل المعاملة وإنشاء القيد المحاسبي بنجاح',
            'journal_entry_id': journal_entry.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@financial_bp.route('/financial/transfer_to_preparation', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def transfer_transaction_to_preparation():
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

        return jsonify({'success': True, 'message': 'تم إضافة المعاملة إلى تحضير الدوام'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@financial_bp.route('/financial/dashboard')
@login_required
@role_required('admin', 'finance')
def financial_dashboard():
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


@financial_bp.route('/meal-deductions')
@login_required
@role_required('owner', 'finance')
def meal_deductions_list():
    from datetime import date

    meal_deductions = MealDeduction.query.order_by(
        MealDeduction.deduction_date.desc()
    ).all()

    settings = []
    if hasattr(MealDeductionSetting, 'query'):
        settings = MealDeductionSetting.query.filter_by(
            is_active=True
        ).all()

    employees = Employee.query.filter_by(is_active=True).all()

    cafeteria_total = 0
    restaurant_total = 0
    meal_total = 0
    total_all = 0
    transferred_total = 0
    transferred_count = 0

    for m in meal_deductions:
        amount = m.amount or 0
        total_all += amount

        if m.is_transferred:
            transferred_total += amount
            transferred_count += 1

        if m.deduction_type == 'cafeteria':
            if not m.is_transferred:
                cafeteria_total += amount

        elif m.deduction_type == 'restaurant':
            if not m.is_transferred:
                restaurant_total += amount

        elif m.deduction_type == 'meal':
            if not m.is_transferred:
                meal_total += amount

    meal_deductions_stats = {
        'total': total_all,
        'count': len(meal_deductions),
        'transferred_rate': (
            (transferred_count / len(meal_deductions)) * 100
            if meal_deductions else 0
        )
    }

    stats = {
        'total_cafeteria': cafeteria_total,
        'total_restaurant': restaurant_total,
        'total_meal': meal_total,
        'total_all': total_all,
        'transferred': transferred_total
    }

    return render_template(
        'financial/meal_deductions.html',
        meal_deductions=meal_deductions,
        meal_deductions_stats=meal_deductions_stats,
        settings=settings,
        employees=employees,
        stats=stats,
        today=date.today(),
        now=datetime.now()
    )


@financial_bp.route('/meal-deductions/add', methods=['POST'])
@login_required
@role_required('owner', 'finance')
def add_meal_deduction():
    try:
        data = request.get_json()
        if not data:
            data = request.form

        employee_ids = data.get('employee_ids', [])
        if isinstance(employee_ids, str):
            employee_ids = [employee_ids]

        deduction_type = data.get('deduction_type')
        amount = float(data.get('amount', 0))
        deduction_date = datetime.strptime(
            data.get('deduction_date'),
            '%Y-%m-%d'
        ).date()

        description = data.get('description', '')

        if not employee_ids or not deduction_type or amount <= 0:
            return jsonify({
                'success': False,
                'message': 'بيانات غير مكتملة'
            }), 400

        ACCOUNT_MAP = {
            'meal': {
                'expense': '511008',
                'receivable': '130002'
            },
            'cafeteria': {
                'expense': '511009',
                'receivable': '130003'
            },
            'restaurant': {
                'expense': '511010',
                'receivable': '130004'
            }
        }

        if deduction_type not in ACCOUNT_MAP:
            return jsonify({
                'success': False,
                'message': 'نوع الخصم غير مدعوم'
            }), 400

        accounts = ACCOUNT_MAP[deduction_type]

        created_count = 0

        for emp_id in employee_ids:
            deduction = MealDeduction(
                employee_id=int(emp_id),
                deduction_type=deduction_type,
                amount=amount,
                deduction_date=deduction_date,
                description=description,
                expense_account_code=accounts['expense'],
                receivable_account_code=accounts['receivable'],
                is_transferred=False
            )

            db.session.add(deduction)
            created_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'✅ تم إضافة {created_count} خصم ({deduction_type}) بنجاح',
            'type': deduction_type,
            'amount': amount
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@financial_bp.route('/contracts/generate-monthly-invoices')
@login_required
@role_required('admin', 'finance')
def generate_monthly_invoices():
    flash('⚠️ هذه الميزة معطلة حالياً. يتم إنشاء الفواتير يدوياً فقط.', 'warning')
    return redirect(url_for('financial.contracts_list'))


@financial_bp.route('/contracts/generate-all-future-invoices/<int:contract_id>')
@login_required
@role_required('admin', 'finance')
def generate_all_future_invoices(contract_id):
    flash('⚠️ هذه الميزة معطلة حالياً. يتم إنشاء الفواتير يدوياً فقط.', 'warning')
    return redirect(url_for('financial.contracts_list'))


@financial_bp.route('/contracts/auto-generate/<int:contract_id>')
@login_required
@role_required('admin', 'finance')
def auto_generate_contract_invoices(contract_id):
    flash('⚠️ هذه الميزة معطلة حالياً. يتم إنشاء الفواتير يدوياً فقط.', 'warning')
    return redirect(url_for('financial.contracts_list'))


@financial_bp.route('/financial/cash/settle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def settle_cash():
    cash_account = Account.query.filter_by(code='110001').first()
    if not cash_account:
        cash_account = Account(
            code='110001', name='Cash', name_ar='الصندوق',
            account_type='asset', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(cash_account)
        db.session.commit()

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
                return redirect(url_for('financial.settle_cash'))

            if transaction_type == 'deposit':
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

            else:
                current_balance = cash_account.get_balance()
                if current_balance < amount:
                    flash(f'⚠️ الرصيد غير كافٍ. المتوفر: {current_balance:,.2f} ريال', 'danger')
                    return redirect(url_for('financial.settle_cash'))

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

        return redirect(url_for('financial.settle_cash'))

    current_balance = cash_account.get_balance()
    return render_template('financial/settle_cash.html',
                           cash_balance=current_balance,
                           cash_entries=cash_entries,
                           now=datetime.now())


@financial_bp.route('/financial/collect-customers', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def collect_customers():
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

        detail1 = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=target_account.id,
            debit=amount,
            credit=0,
            description='تحصيل من العملاء'
        )
        db.session.add(detail1)

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


@financial_bp.route('/contracts')
@login_required
@role_required('admin', 'finance')
def contracts_list():
    if current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            contracts = Contract.query.filter_by(company_id=supervisor_employee.company_id).all()
        else:
            contracts = []
    else:
        contracts = Contract.query.all()
    return render_template('contracts/contracts.html', contracts=contracts)


@financial_bp.route('/contracts/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def add_contract():
    if request.method == 'POST':
        company_id = request.form.get('company_id')

        company = Company.query.get(company_id)
        if not company:
            flash('الشركة غير موجودة', 'danger')
            return redirect(url_for('financial.add_contract'))

        contract = Contract(
            company_id=company_id,
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

        flash(f'✅ تم إضافة العقد بنجاح (بدون قيود محاسبية ولا فواتير)', 'success')
        flash('ℹ️ ملاحظة: سيتم إنشاء الفواتير يدوياً لاحقاً عند الحاجة', 'info')
        return redirect(url_for('financial.contracts_list'))

    companies = Company.query.all()
    return render_template('contracts/add_contract.html', companies=companies)


@financial_bp.route('/invoices')
@login_required
@role_required('admin', 'finance')
def invoices_list():
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


@financial_bp.route('/invoices/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def add_invoice():
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

            try:
                journal_entry = create_invoice_journal_entry(invoice)
                invoice.journal_entry_id = journal_entry.id
                invoice.is_posted_to_accounts = True
            except Exception as je:
                db.session.rollback()
                flash(f'تمت إضافة الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                return redirect(url_for('financial.invoices_list'))

            db.session.commit()
            flash('✅ تم إضافة الفاتورة والقيد المحاسبي بنجاح', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('financial.add_invoice'))

        return redirect(url_for('financial.invoices_list'))

    contracts = Contract.query.filter_by(status='active').all()
    return render_template('contracts/add_invoice.html', contracts=contracts)


@financial_bp.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    if request.method == 'POST':
        try:
            invoice.invoice_number = request.form.get('invoice_number')
            invoice.amount = float(request.form.get('amount'))
            invoice.invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()

            if request.form.get('due_date'):
                invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
            else:
                invoice.due_date = None

            invoice.notes = request.form.get('notes')

            new_contract_id = request.form.get('contract_id')
            if new_contract_id and int(new_contract_id) != invoice.contract_id:
                old_contract = Contract.query.get(invoice.contract_id)
                if old_contract:
                    old_contract.amount_received -= invoice.amount
                    old_contract.remaining_amount = old_contract.contract_value - old_contract.amount_received
                    if old_contract.remaining_amount > 0:
                        old_contract.status = 'active'
                    elif old_contract.remaining_amount == 0:
                        old_contract.status = 'completed'

                invoice.contract_id = int(new_contract_id)
                new_contract = Contract.query.get(invoice.contract_id)
                if new_contract:
                    new_contract.amount_received += invoice.amount
                    new_contract.remaining_amount = new_contract.contract_value - new_contract.amount_received
                    if new_contract.remaining_amount <= 0:
                        new_contract.status = 'completed'
            else:
                contract = Contract.query.get(invoice.contract_id)
                if contract:
                    total_invoices = sum(i.amount for i in contract.invoices if i.id != invoice.id) + invoice.amount
                    contract.amount_received = total_invoices
                    contract.remaining_amount = contract.contract_value - total_invoices
                    if contract.remaining_amount <= 0:
                        contract.status = 'completed'
                    elif contract.status == 'completed':
                        contract.status = 'active'

            db.session.commit()
            flash('✅ تم تحديث الفاتورة بنجاح', 'success')
            return redirect(url_for('financial.invoices_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    contracts = Contract.query.all()
    return render_template('contracts/edit_invoice.html',
                           invoice=invoice,
                           contracts=contracts,
                           now=datetime.now())


@financial_bp.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def delete_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

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
        return redirect(url_for('financial.invoices_list'))

    try:
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

    return redirect(url_for('financial.invoices_list'))


@financial_bp.route('/invoices/pay/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def pay_invoice(invoice_id):
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
                return redirect(url_for('financial.pay_invoice', invoice_id=invoice_id))

            if paid_amount > remaining:
                flash('المبلغ المدفوع يتجاوز المبلغ المتبقي', 'danger')
                return redirect(url_for('financial.pay_invoice', invoice_id=invoice_id))

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

            try:
                create_invoice_payment_journal_entry(invoice, paid_amount, payment_method)
            except Exception as je:
                db.session.rollback()
                flash(f'تم تسديد الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
                return redirect(url_for('financial.invoices_list'))

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

        return redirect(url_for('financial.invoices_list'))

    remaining_amount = invoice.amount - (invoice.paid_amount or 0)
    return render_template('contracts/pay_invoice.html',
                           invoice=invoice,
                           remaining_amount=remaining_amount,
                           now=datetime.now())


@financial_bp.route('/invoices/print/<int:invoice_id>')
@login_required
def print_invoice(invoice_id):
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


@financial_bp.route('/invoices/reverse/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def reverse_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)

    if not invoice.has_journal_entry():
        flash('⚠️ هذه الفاتورة ليس لها قيد محاسبي لعكسه', 'danger')
        return redirect(url_for('financial.invoices_list'))

    if invoice.is_paid:
        flash('⚠️ لا يمكن عكس قيد فاتورة مدفوعة', 'danger')
        return redirect(url_for('financial.invoices_list'))

    try:
        reverse_entry = reverse_invoice_journal_entry(invoice)

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

        flash(f'✅ تم عكس القيد المحاسبي (رقم: {reverse_entry.entry_number}) وحذف الفاتورة بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

    return redirect(url_for('financial.invoices_list'))


@financial_bp.route('/financial/salaries/export')
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
