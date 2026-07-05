from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Account, JournalEntry, JournalEntryDetail, Company, Supplier, Salary, Invoice, SupplierInvoice, SupplierInvoicePayment, FinancialTransaction
from utils import role_required, create_journal_entry, auto_close_expenses, redistribute_expenses, reverse_journal_entry, get_next_entry_number

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/accounts')
@login_required
@role_required('admin', 'finance')
def accounts_dashboard():
    from sqlalchemy import func

    accounts_count = Account.query.filter_by(is_active=True).count()
    journal_entries_count = JournalEntry.query.count()

    assets = Account.query.filter_by(account_type='asset', is_active=True).all()
    total_assets = sum(a.get_balance() for a in assets)

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


@accounts_bp.route('/accounts/chart')
@login_required
@role_required('admin', 'finance')
def chart_of_accounts():
    from sqlalchemy import func

    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()

    def flatten_accounts(account_list):
        result = []
        for acc in account_list:
            result.append(acc)
            if hasattr(acc, 'children') and acc.children:
                result.extend(flatten_accounts(acc.children))
        return result

    def build_tree(parent_id=None, level=0):
        tree = []
        for acc in accounts:
            if acc.parent_id == parent_id:
                acc.level = level
                acc.children = build_tree(acc.id, level + 1)
                tree.append(acc)
        return tree

    account_tree = build_tree()

    all_accounts = flatten_accounts(account_tree)

    customer_accounts_count = 0
    supplier_accounts_count = 0
    total_assets = 0
    total_liabilities = 0
    total_equity = 0
    total_revenue = 0

    for acc in all_accounts:
        balance = acc.get_balance()

        if acc.code and acc.code.startswith('1201'):
            customer_accounts_count += 1
        elif acc.code and (acc.code.startswith('2201') or acc.code.startswith('2202')):
            supplier_accounts_count += 1

        if acc.account_type == 'asset':
            total_assets += balance
        elif acc.account_type == 'liability':
            total_liabilities += balance
        elif acc.account_type == 'equity':
            total_equity += balance
        elif acc.account_type == 'revenue':
            total_revenue += balance

    companies_with_accounts = []
    total_companies_balance = 0

    companies = Company.query.all()
    for company in companies:
        account = company.get_or_create_receivable_account()
        if account and account.is_active:
            balance = account.get_balance()
            companies_with_accounts.append({
                'company': company,
                'account': account,
                'balance': balance
            })
            total_companies_balance += balance

    if not companies_with_accounts:
        customer_sub_accounts = Account.query.filter(
            Account.code.startswith('1201'),
            Account.is_active == True
        ).all()
        for acc in customer_sub_accounts:
            balance = acc.get_balance()
            company = Company.query.filter_by(receivable_account_id=acc.id).first()
            if not company:
                company = type('obj', (object,), {
                    'id': 0,
                    'name': acc.name_ar.replace('ذمم مدينة - ', ''),
                    'phone': None,
                    'contact_person': None
                })()
            companies_with_accounts.append({
                'company': company,
                'account': acc,
                'balance': balance
            })
            total_companies_balance += balance

    suppliers_with_accounts = []
    total_suppliers_balance = 0

    suppliers = Supplier.query.filter_by(is_active=True).all()
    for supplier in suppliers:
        account = supplier.get_or_create_payable_account()
        if account and account.is_active:
            balance = account.get_balance()
            suppliers_with_accounts.append({
                'supplier': supplier,
                'account': account,
                'balance': balance
            })
            total_suppliers_balance += balance

    if not suppliers_with_accounts:
        supplier_sub_accounts = Account.query.filter(
            Account.code.startswith('2202'),
            Account.is_active == True
        ).all()
        for acc in supplier_sub_accounts:
            balance = acc.get_balance()
            supplier = Supplier.query.filter_by(payable_account_id=acc.id).first()
            if not supplier:
                supplier = type('obj', (object,), {
                    'id': 0,
                    'name_ar': acc.name_ar.replace('ذمم دائنة - ', ''),
                    'phone': None,
                    'name': acc.name
                })()
            suppliers_with_accounts.append({
                'supplier': supplier,
                'account': acc,
                'balance': balance
            })
            total_suppliers_balance += balance

    return render_template('accounts/chart_of_accounts.html',
                           accounts=account_tree,
                           account_types=Account.ACCOUNT_TYPES,
                           customer_accounts_count=customer_accounts_count,
                           supplier_accounts_count=supplier_accounts_count,
                           total_assets=total_assets,
                           total_liabilities=total_liabilities,
                           total_equity=total_equity,
                           total_revenue=total_revenue,
                           companies_with_accounts=companies_with_accounts,
                           suppliers_with_accounts=suppliers_with_accounts,
                           total_companies_balance=total_companies_balance,
                           total_suppliers_balance=total_suppliers_balance,
                           now=datetime.now())


@accounts_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_account():
    if request.method == 'POST':
        try:
            existing = Account.query.filter_by(code=request.form.get('code')).first()
            if existing:
                flash('⚠️ رقم الحساب موجود مسبقاً', 'danger')
                return redirect(url_for('accounts.add_account'))

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
            return redirect(url_for('accounts.chart_of_accounts'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    parent_accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    return render_template('accounts/add_account.html',
                           parent_accounts=parent_accounts,
                           account_types=Account.ACCOUNT_TYPES,
                           natures={'debit': 'مدين', 'credit': 'دائن'},
                           now=datetime.now())


@accounts_bp.route('/accounts/edit/<int:account_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)

    if request.method == 'POST':
        try:
            existing = Account.query.filter(
                Account.code == request.form.get('code'),
                Account.id != account_id
            ).first()
            if existing:
                flash('⚠️ رقم الحساب موجود مسبقاً لحساب آخر', 'danger')
                return redirect(url_for('accounts.edit_account', account_id=account_id))

            account.code = request.form.get('code')
            account.name = request.form.get('name')
            account.name_ar = request.form.get('name_ar')
            account.account_type = request.form.get('account_type')
            account.nature = request.form.get('nature')
            account.parent_id = request.form.get('parent_id') or None
            account.notes = request.form.get('notes')

            if 'opening_balance' in request.form:
                account.opening_balance = float(request.form.get('opening_balance', 0))

            db.session.commit()
            flash(f'✅ تم تعديل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
            return redirect(url_for('accounts.chart_of_accounts'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

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


@accounts_bp.route('/accounts/delete/<int:account_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_account(account_id):
    account = Account.query.get_or_404(account_id)

    journal_entries = JournalEntryDetail.query.filter_by(account_id=account.id).count()
    if journal_entries > 0:
        flash(
            f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بـ {journal_entries} قيد محاسبي',
            'danger')
        return redirect(url_for('accounts.chart_of_accounts'))

    transactions = FinancialTransaction.query.filter_by(employee_id=account.id).count()
    if transactions > 0:
        flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بمعاملات مالية', 'danger')
        return redirect(url_for('accounts.chart_of_accounts'))

    invoices = Invoice.query.filter_by(contract_id=account.id).count()
    if invoices > 0:
        flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بفواتير', 'danger')
        return redirect(url_for('accounts.chart_of_accounts'))

    supplier_invoices = SupplierInvoice.query.filter_by(supplier_id=account.id).count()
    if supplier_invoices > 0:
        flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه مرتبط بفواتير موردين', 'danger')
        return redirect(url_for('accounts.chart_of_accounts'))

    children = Account.query.filter_by(parent_id=account.id, is_active=True).count()
    if children > 0:
        flash(f'⚠️ لا يمكن حذف الحساب {account.code} - {account.name_ar} لأنه يحتوي على {children} حسابات فرعية',
              'danger')
        return redirect(url_for('accounts.chart_of_accounts'))

    account.is_active = False
    db.session.commit()

    flash(f'✅ تم تعطيل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
    return redirect(url_for('accounts.chart_of_accounts'))


@accounts_bp.route('/accounts/activate/<int:account_id>', methods=['POST'])
@login_required
@role_required('admin')
def activate_account(account_id):
    account = Account.query.get_or_404(account_id)
    account.is_active = True
    db.session.commit()
    flash(f'✅ تم تفعيل الحساب {account.code} - {account.name_ar} بنجاح', 'success')
    return redirect(url_for('accounts.chart_of_accounts'))


@accounts_bp.route('/accounts/journal')
@login_required
@role_required('admin', 'finance')
def journal_entries_list():
    from models import Account

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = JournalEntry.query

    if start_date:
        query = query.filter(JournalEntry.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(JournalEntry.date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    entries = query.order_by(JournalEntry.date.desc(), JournalEntry.entry_number.desc()).all()

    for entry in entries:
        entry.has_reverse = JournalEntry.query.filter(
            JournalEntry.reference_type == 'reverse',
            JournalEntry.reference_id == entry.id
        ).first() is not None

    total_debit = sum(entry.get_total_debit() for entry in entries)
    total_credit = sum(entry.get_total_credit() for entry in entries)

    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()

    return render_template('accounts/journal_entries.html',
                           entries=entries,
                           accounts=accounts,
                           total_debit=total_debit,
                           total_credit=total_credit,
                           start_date=start_date,
                           end_date=end_date)


@accounts_bp.route('/accounts/journal/add', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def add_journal_entry():
    try:
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        description = request.form.get('description')
        reference_type = request.form.get('reference_type') or None

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
            return redirect(url_for('accounts.journal_entries_list'))

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

    return redirect(url_for('accounts.journal_entries_list'))


@accounts_bp.route('/accounts/reverse_entry/<int:entry_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def reverse_journal_entry_view(entry_id):
    original_entry = JournalEntry.query.get_or_404(entry_id)

    reversed_exists = JournalEntry.query.filter(
        JournalEntry.reference_type == 'reverse',
        JournalEntry.reference_id == original_entry.id
    ).first()

    if reversed_exists:
        flash(f'⚠️ هذا القيد تم عكسه مسبقاً في القيد رقم: {reversed_exists.entry_number}', 'warning')
        return redirect(url_for('accounts.journal_entries_list'))

    try:
        reverse_entry = reverse_journal_entry(original_entry.id)

        flash(f'✅ تم عكس القيد {original_entry.entry_number} بنجاح', 'success')
        flash(f'📋 القيد العكسي: {reverse_entry.entry_number}', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء عكس القيد: {str(e)}', 'danger')

    return redirect(url_for('accounts.journal_entries_list'))


@accounts_bp.route('/accounts/transfer', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def transfer_between_accounts():
    try:
        from_account_id = int(request.form.get('from_account_id'))
        to_account_id = int(request.form.get('to_account_id'))
        amount = float(request.form.get('amount'))
        description = request.form.get('description')

        from_account = Account.query.get(from_account_id)
        to_account = Account.query.get(to_account_id)

        if not from_account or not to_account:
            flash('❌ الحسابات غير موجودة', 'danger')
            return redirect(url_for('accounts.journal_entries_list'))

        if from_account_id == to_account_id:
            flash('⚠️ لا يمكن التحويل لنفس الحساب', 'danger')
            return redirect(url_for('accounts.journal_entries_list'))

        if from_account.nature == 'debit':
            current_balance = from_account.get_balance()
            if current_balance < amount:
                flash(f'⚠️ الرصيد غير كافٍ في حساب {from_account.name_ar}. المتوفر: {current_balance:,.2f}',
                      'danger')
                return redirect(url_for('accounts.journal_entries_list'))

        entries = [
            (to_account.id, amount, 0, f'استلام من {from_account.name_ar}'),
            (from_account.id, 0, amount, f'تحويل إلى {to_account.name_ar}')
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

    return redirect(url_for('accounts.journal_entries_list'))


@accounts_bp.route('/api/journal-entry/<int:entry_id>')
@login_required
def get_journal_entry_api(entry_id):
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


@accounts_bp.route('/accounts/zero-out', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def zero_out_account():
    try:
        account_id = int(request.form.get('account_id'))
        target_account_id = int(request.form.get('target_account_id'))

        account = Account.query.get(account_id)
        target_account = Account.query.get(target_account_id)

        if not account or not target_account:
            flash('❌ الحسابات غير موجودة', 'danger')
            return redirect(url_for('accounts.journal_entries_list'))

        if account_id == target_account_id:
            flash('⚠️ لا يمكن تصفير الحساب لنفسه', 'danger')
            return redirect(url_for('accounts.journal_entries_list'))

        current_balance = account.get_balance()

        if current_balance == 0:
            flash(f'⚠️ حساب {account.name_ar} رصيده صفر بالفعل', 'warning')
            return redirect(url_for('accounts.journal_entries_list'))

        amount = abs(current_balance)

        if account.nature == 'debit' and current_balance > 0:
            entries = [
                (account.id, amount, 0, f'تصفير حساب {account.name_ar}'),
                (target_account.id, 0, amount, f'استلام رصيد من {account.name_ar}')
            ]
            description = f'تصفير حساب {account.name_ar} (رصيد مدين {amount:,.2f}) إلى {target_account.name_ar}'
        elif account.nature == 'debit' and current_balance < 0:
            entries = [
                (account.id, 0, amount, f'تصفير حساب {account.name_ar}'),
                (target_account.id, amount, 0, f'تحويل رصيد من {account.name_ar}')
            ]
            description = f'تصفير حساب {account.name_ar} (رصيد دائن {amount:,.2f}) إلى {target_account.name_ar}'
        elif account.nature == 'credit' and current_balance > 0:
            entries = [
                (account.id, 0, amount, f'تصفير حساب {account.name_ar}'),
                (target_account.id, amount, 0, f'تحويل رصيد من {account.name_ar}')
            ]
            description = f'تصفير حساب {account.name_ar} (رصيد دائن {amount:,.2f}) إلى {target_account.name_ar}'
        else:
            entries = [
                (account.id, amount, 0, f'تصفير حساب {account.name_ar}'),
                (target_account.id, 0, amount, f'استلام رصيد من {account.name_ar}')
            ]
            description = f'تصفير حساب {account.name_ar} (رصيد مدين {amount:,.2f}) إلى {target_account.name_ar}'

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

    return redirect(url_for('accounts.journal_entries_list'))


@accounts_bp.route('/accounts/transfer-history')
@login_required
@role_required('admin', 'finance')
def transfer_history():
    transfers = JournalEntry.query.filter(
        JournalEntry.reference_type.in_(['transfer', 'zero_out'])
    ).order_by(JournalEntry.date.desc()).all()

    return render_template('accounts/transfer_history.html', transfers=transfers)


def get_equity_account():
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
    expense = Account.query.filter_by(code='530005').first()
    if not expense:
        expense = Account(
            code='530005', name='General Expense', name_ar='مصروفات عامة',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(expense)
        db.session.commit()
    return expense


@accounts_bp.route('/accounts/trial_balance')
@login_required
@role_required('admin', 'finance')
def trial_balance():
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


@accounts_bp.route('/accounts/income_statement')
@login_required
@role_required('admin', 'finance')
def income_statement():
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


@accounts_bp.route('/accounts/balance_sheet')
@login_required
@role_required('admin', 'finance')
def balance_sheet():
    from models import JournalEntry

    as_of_date = request.args.get('as_of_date')

    if not as_of_date:
        as_of_date = datetime.now().date()
    else:
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()

    assets = Account.query.filter_by(account_type='asset', is_active=True).all()
    liabilities = Account.query.filter_by(account_type='liability', is_active=True).all()
    equity = Account.query.filter_by(account_type='equity', is_active=True).all()

    asset_data = []
    liability_data = []
    equity_data = []

    total_assets = 0
    total_liabilities = 0
    total_equity = 0

    for acc in assets:
        balance = acc.get_balance(as_of_date)
        asset_data.append({'account': acc, 'balance': balance})
        total_assets += balance

    for acc in liabilities:
        balance = acc.get_balance(as_of_date)
        if 'الرواتب المصروفة' not in acc.name_ar:
            liability_data.append({'account': acc, 'balance': balance})
            total_liabilities += balance

    for acc in equity:
        balance = acc.get_balance(as_of_date)
        equity_data.append({'account': acc, 'balance': balance})
        total_equity += balance

    difference = total_assets - (total_liabilities + total_equity)
    is_balanced = abs(difference) < 0.01

    closing_entry = JournalEntry.query.filter_by(
        reference_type='closing_expenses'
    ).order_by(JournalEntry.entry_number.desc()).first()

    is_closed = False
    if closing_entry:
        reopen_entry = JournalEntry.query.filter_by(
            reference_type='reopen_period',
            reference_id=closing_entry.id
        ).first()
        is_closed = reopen_entry is None

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


@accounts_bp.route('/accounts/close-expenses', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def close_expenses_api():
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


@accounts_bp.route('/accounts/reopen-period', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def reopen_period_api():
    try:
        closing_entry = JournalEntry.query.filter_by(
            reference_type='closing_expenses'
        ).order_by(JournalEntry.entry_number.desc()).first()

        if not closing_entry:
            return jsonify({
                'success': False,
                'error': 'لا يوجد قيد إقفال لعكسه. المصروفات غير مقفلة.'
            }), 400

        existing_reverse = JournalEntry.query.filter(
            JournalEntry.reference_type == 'reopen_period',
            JournalEntry.reference_id == closing_entry.id
        ).first()

        if existing_reverse:
            return jsonify({
                'success': False,
                'error': f'تم فتح الفترة مسبقاً بالقيد {existing_reverse.entry_number}'
            }), 400

        reverse_entry = reverse_journal_entry(closing_entry.id)

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


@accounts_bp.route('/accounts/redistribute-expenses', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def redistribute_expenses_api():
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


@accounts_bp.route('/accounts/expense-details', methods=['GET'])
@login_required
@role_required('admin', 'finance')
def get_expense_details():
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


@accounts_bp.route('/accounts/check-closing-status', methods=['GET'])
@login_required
@role_required('admin', 'finance')
def check_closing_status():
    from models import JournalEntry

    closing_entry = JournalEntry.query.filter_by(
        reference_type='closing_expenses'
    ).order_by(JournalEntry.entry_number.desc()).first()

    reopen_entry = None
    if closing_entry:
        reopen_entry = JournalEntry.query.filter_by(
            reference_type='reopen_period',
            reference_id=closing_entry.id
        ).first()

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


@accounts_bp.route('/accounts/cash_flow')
@login_required
@role_required('admin', 'finance')
def cash_flow_statement():
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

    cash_inflows = []

    contract_payments = JournalEntryDetail.query.join(JournalEntry).filter(
        JournalEntry.date >= start_date,
        JournalEntry.date <= end_date,
        JournalEntryDetail.credit > 0
    ).join(Account).filter(Account.account_type == 'revenue').all()

    total_inflows = sum(p.credit for p in contract_payments)

    cash_outflows = []

    salaries_paid = Salary.query.filter(
        Salary.paid_date >= start_date,
        Salary.paid_date <= end_date,
        Salary.is_paid == True
    ).all()
    total_salaries = sum(s.total_salary for s in salaries_paid)

    supplier_payments = SupplierInvoicePayment.query.filter(
        SupplierInvoicePayment.payment_date >= start_date,
        SupplierInvoicePayment.payment_date <= end_date
    ).all()
    total_supplier_payments = sum(p.amount for p in supplier_payments)

    total_outflows = total_salaries + total_supplier_payments

    net_cash_flow = total_inflows - total_outflows

    return render_template('accounts/cash_flow.html',
                           start_date=start_date,
                           end_date=end_date,
                           total_inflows=total_inflows,
                           total_outflows=total_outflows,
                           net_cash_flow=net_cash_flow,
                           salaries_paid=salaries_paid,
                           supplier_payments=supplier_payments,
                           contract_payments=contract_payments,
                           now=datetime.now())
