from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from models import Supplier, SupplierInvoice, SupplierInvoicePayment, ExpenseCategory, Account, JournalEntry, JournalEntryDetail
from utils import role_required, get_next_entry_number, create_supplier_invoice_payment_journal_entry
from models import db

suppliers_bp = Blueprint('suppliers', __name__)


def generate_supplier_invoice_number():
    last_invoice = SupplierInvoice.query.order_by(SupplierInvoice.id.desc()).first()

    if last_invoice and last_invoice.invoice_number:
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

    today = datetime.now()
    date_str = today.strftime('%Y%m%d')

    invoice_number = f"SI-{date_str}-{str(new_num).zfill(3)}"

    return invoice_number


@suppliers_bp.route('/suppliers')
@login_required
@role_required('admin', 'finance')
def suppliers_list():
    suppliers = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()
    return render_template('suppliers/suppliers.html', suppliers=suppliers, now=datetime.now())


@suppliers_bp.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def edit_supplier(supplier_id):
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
            return redirect(url_for('suppliers.suppliers_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return render_template('suppliers/edit_supplier.html', supplier=supplier, now=datetime.now())


@suppliers_bp.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.is_active = False
    db.session.commit()
    flash('✅ تم حذف المورد بنجاح', 'success')
    return redirect(url_for('suppliers.suppliers_list'))


@suppliers_bp.route('/supplier-invoices')
@login_required
@role_required('admin', 'finance')
def supplier_invoices_list():
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


@suppliers_bp.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def add_supplier():
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
            db.session.flush()

            supplier.get_or_create_payable_account()

            db.session.commit()
            flash('✅ تم إضافة المورد وإنشاء حسابه الفرعي بنجاح', 'success')
            return redirect(url_for('suppliers.suppliers_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return render_template('suppliers/add_supplier.html', now=datetime.now())


@suppliers_bp.route('/supplier-invoices/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'accountant'])
def add_supplier_invoice():
    from models import Supplier, ExpenseCategory, Account, JournalEntry, JournalEntryDetail, SupplierInvoice
    from datetime import datetime
    from utils import get_next_entry_number

    if request.method == 'POST':
        try:
            supplier_id = request.form.get('supplier_id')
            category_id = request.form.get('category_id')
            amount = float(request.form.get('amount'))
            invoice_number = request.form.get('invoice_number')
            invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d')
            due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d') if request.form.get(
                'due_date') else None
            notes = request.form.get('notes')

            supplier = Supplier.query.get(supplier_id)
            if not supplier:
                flash('❌ المورد غير موجود', 'danger')
                return redirect(url_for('suppliers.add_supplier_invoice'))

            invoice = SupplierInvoice(
                supplier_id=supplier_id,
                category_id=category_id if category_id else None,
                amount=amount,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                paid_amount=0,
                remaining_amount=amount,
                status='pending',
                notes=notes,
                created_by=current_user.id
            )
            db.session.add(invoice)
            db.session.flush()

            expense_account = Account.query.filter_by(code='530005').first()

            if category_id:
                category = ExpenseCategory.query.get(category_id)
                if category and category.account_code:
                    expense_account = Account.query.filter_by(code=category.account_code).first()

            if not expense_account:
                expense_account = Account.query.filter_by(code='530005').first()
                if not expense_account:
                    expense_account = Account(
                        code='530005',
                        name='General Expense',
                        name_ar='مصروفات عامة',
                        account_type='expense',
                        nature='debit',
                        opening_balance=0,
                        is_active=True
                    )
                    db.session.add(expense_account)
                    db.session.flush()

            supplier_account = supplier.get_or_create_payable_account()

            entry_number = get_next_entry_number()

            je = JournalEntry(
                entry_number=entry_number,
                date=invoice_date,
                description=f"فاتورة مورد {invoice_number} - {supplier.name_ar}",
                reference_type='supplier_invoice',
                reference_id=invoice.id,
                created_by=current_user.id
            )
            db.session.add(je)
            db.session.flush()

            debit_detail = JournalEntryDetail(
                entry_id=je.id,
                account_id=expense_account.id,
                debit=amount,
                credit=0,
                description=f'فاتورة {invoice_number} - {supplier.name_ar}'
            )
            db.session.add(debit_detail)

            credit_detail = JournalEntryDetail(
                entry_id=je.id,
                account_id=supplier_account.id,
                debit=0,
                credit=amount,
                description=f'استحقاق فاتورة {invoice_number}'
            )
            db.session.add(credit_detail)

            invoice.journal_entry_id = je.id
            db.session.commit()

            flash(f'✅ تم إضافة فاتورة المورد {invoice_number} بنجاح', 'success')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ: {e}")
            import traceback
            traceback.print_exc()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')
            return redirect(url_for('suppliers.add_supplier_invoice'))

    suppliers = Supplier.query.filter_by(is_active=True).all()
    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    return render_template('suppliers/add_invoice.html',
                           suppliers=suppliers,
                           categories=categories,
                           now=datetime.now())


@suppliers_bp.route('/supplier-invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def edit_supplier_invoice(invoice_id):
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

            invoice.remaining_amount = invoice.amount - invoice.paid_amount
            if invoice.remaining_amount <= 0:
                invoice.status = 'paid'
            elif invoice.paid_amount > 0:
                invoice.status = 'partial'
            else:
                invoice.status = 'pending'

            db.session.commit()
            flash('✅ تم تحديث الفاتورة بنجاح', 'success')
            return redirect(url_for('suppliers.supplier_invoices_list'))

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


@suppliers_bp.route('/supplier-invoices/delete/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_supplier_invoice(invoice_id):
    invoice = SupplierInvoice.query.get_or_404(invoice_id)

    try:
        for payment in invoice.payments:
            db.session.delete(payment)
        db.session.delete(invoice)
        db.session.commit()
        flash('✅ تم حذف الفاتورة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('suppliers.supplier_invoices_list'))


@suppliers_bp.route('/supplier-invoices/pay/<int:invoice_id>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def pay_supplier_invoice(invoice_id):
    from models import Account

    invoice = SupplierInvoice.query.get_or_404(invoice_id)

    try:
        payment_amount = float(request.form.get('payment_amount', 0))
        payment_method = request.form.get('payment_method')
        reference_number = request.form.get('reference_number')

        if payment_amount <= 0:
            flash('⚠️ المبلغ يجب أن يكون أكبر من صفر', 'danger')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        if payment_amount > invoice.remaining_amount:
            flash('⚠️ المبلغ المدفوع يتجاوز المبلغ المتبقي', 'danger')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        if payment_method == 'bank_transfer':
            payment_account = Account.query.filter_by(code='110002').first()
            account_name = "البنك"
        else:
            payment_account = Account.query.filter_by(code='110001').first()
            account_name = "الصندوق"

        if not payment_account:
            flash(f'⚠️ حساب {account_name} غير موجود في النظام', 'danger')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        current_balance = payment_account.get_balance()
        if current_balance < payment_amount:
            flash(f'⚠️ رصيد {account_name} غير كافٍ!', 'danger')
            flash(f'📊 الرصيد المتوفر: {current_balance:,.2f} ريال', 'warning')
            flash(f'💰 المبلغ المطلوب: {payment_amount:,.2f} ريال', 'warning')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        payment = SupplierInvoicePayment(
            invoice_id=invoice.id,
            amount=payment_amount,
            payment_date=datetime.now().date(),
            payment_method=payment_method,
            reference_number=reference_number,
            created_by=current_user.id
        )
        db.session.add(payment)

        invoice.paid_amount += payment_amount
        invoice.remaining_amount -= payment_amount
        invoice.payment_method = payment_method
        invoice.reference_number = reference_number

        if invoice.remaining_amount <= 0:
            invoice.status = 'paid'
        else:
            invoice.status = 'partial'

        db.session.flush()

        try:
            create_supplier_invoice_payment_journal_entry(invoice, payment_amount, payment_method)
            payment.is_posted_to_accounts = True
        except Exception as je:
            db.session.rollback()
            flash(f'تم تسديد الفاتورة ولكن حدث خطأ في القيد المحاسبي: {str(je)}', 'warning')
            return redirect(url_for('suppliers.supplier_invoices_list'))

        db.session.commit()
        flash(f'✅ تم تسديد مبلغ {payment_amount:,.0f} ريال بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('suppliers.supplier_invoices_list'))


@suppliers_bp.route('/supplier-invoices/report')
@login_required
@role_required('admin', 'finance')
def supplier_invoices_report():
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

    total_amount = sum(i.amount for i in invoices)
    total_paid = sum(i.paid_amount for i in invoices)
    total_remaining = sum(i.remaining_amount for i in invoices)

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


@suppliers_bp.route('/expense-categories')
@login_required
@role_required('admin', 'finance')
def expense_categories_list():
    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    return render_template('suppliers/categories.html', categories=categories, now=datetime.now())


@suppliers_bp.route('/expense-categories/add', methods=['POST'])
@login_required
@role_required('admin')
def add_expense_category():
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

    return redirect(url_for('suppliers.expense_categories_list'))


@suppliers_bp.route('/expense-categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_expense_category(category_id):
    category = ExpenseCategory.query.get_or_404(category_id)

    if request.method == 'POST':
        try:
            category.name = request.form.get('name')
            category.name_ar = request.form.get('name_ar')
            category.account_code = request.form.get('account_code')
            category.parent_id = request.form.get('parent_id') or None
            db.session.commit()
            flash('✅ تم تحديث الفئة بنجاح', 'success')
            return redirect(url_for('suppliers.expense_categories_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

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


@suppliers_bp.route('/expense-categories/delete/<int:category_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_expense_category(category_id):
    category = ExpenseCategory.query.get_or_404(category_id)
    category.is_active = False
    db.session.commit()
    flash('✅ تم حذف الفئة بنجاح', 'success')
    return redirect(url_for('suppliers.expense_categories_list'))


@suppliers_bp.route('/expense-categories/toggle/<int:category_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_expense_category(category_id):
    category = ExpenseCategory.query.get_or_404(category_id)
    category.is_active = not category.is_active
    db.session.commit()
    status = 'تفعيل' if category.is_active else 'تعطيل'
    flash(f'✅ تم {status} الفئة بنجاح', 'success')
    return redirect(url_for('suppliers.expense_categories_list'))


@suppliers_bp.route('/supplier-invoices/print/<int:invoice_id>')
@login_required
@role_required('admin', 'finance')
def print_supplier_invoice(invoice_id):
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
