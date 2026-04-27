from app import app
from models import db, Account, JournalEntry, JournalEntryDetail, Invoice, Contract
from datetime import datetime
from utils import get_next_entry_number

with app.app_context():
    print('=' * 60)
    print('إعادة إنشاء قيد الفاتورة وقيد الدفع')
    print('=' * 60)

    # ========== 1. البحث عن الفاتورة ==========
    invoice = Invoice.query.filter_by(invoice_number='86444').first()

    if not invoice:
        print('❌ لم يتم العثور على الفاتورة رقم 86444')
        exit()

    print(f'\n📄 الفاتورة:')
    print(f'   رقم: {invoice.invoice_number}')
    print(f'   المبلغ: {invoice.amount:,.0f} ريال')
    print(f'   الحالة: {"مدفوعة" if invoice.is_paid else "غير مدفوعة"}')

    # ========== 2. البحث عن الحسابات ==========
    customers = Account.query.filter_by(code='120001').first()
    if not customers:
        customers = Account(
            code='120001', name='Customers', name_ar='العملاء',
            account_type='asset', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(customers)

    revenue_account = Account.query.filter_by(code='410003').first()
    if not revenue_account:
        revenue_account = Account(
            code='410003', name='Quarterly Contract Revenue', name_ar='إيرادات العقود الربع سنوية',
            account_type='revenue', nature='credit', opening_balance=0, is_active=True
        )
        db.session.add(revenue_account)

    bank_account = Account.query.filter_by(code='110002').first()
    if not bank_account:
        bank_account = Account(
            code='110002', name='Bank Account', name_ar='البنك',
            account_type='asset', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(bank_account)

    db.session.commit()

    # ========== 3. إنشاء قيد الفاتورة (استحقاق) ==========
    print('\n📝 إنشاء قيد الفاتورة...')

    entry_number1 = get_next_entry_number()

    invoice_entry = JournalEntry(
        entry_number=entry_number1,
        date=invoice.invoice_date,
        description=f'فاتورة رقم {invoice.invoice_number} - عميل',
        reference_type='invoice',
        reference_id=invoice.id
    )
    db.session.add(invoice_entry)
    db.session.flush()

    # مدين: العملاء
    detail1 = JournalEntryDetail(
        entry_id=invoice_entry.id,
        account_id=customers.id,
        debit=invoice.amount,
        credit=0,
        description=f'فاتورة رقم {invoice.invoice_number}'
    )
    db.session.add(detail1)

    # دائن: إيرادات العقود
    detail2 = JournalEntryDetail(
        entry_id=invoice_entry.id,
        account_id=revenue_account.id,
        debit=0,
        credit=invoice.amount,
        description=f'إيرادات فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail2)

    db.session.commit()

    print(f'   ✅ قيد الفاتورة: {invoice_entry.entry_number}')
    print(f'      مدين: العملاء (120001): {invoice.amount:,.0f} ريال')
    print(f'      دائن: إيرادات العقود (410003): {invoice.amount:,.0f} ريال')

    # ربط القيد بالفاتورة
    invoice.journal_entry_id = invoice_entry.id
    db.session.commit()

    # ========== 4. إنشاء قيد الدفع (تحصيل) ==========
    print('\n📝 إنشاء قيد الدفع...')

    entry_number2 = get_next_entry_number()

    payment_entry = JournalEntry(
        entry_number=entry_number2,
        date=invoice.paid_date or datetime.now().date(),
        description=f'تسديد فاتورة رقم {invoice.invoice_number} - تحويل بنكي',
        reference_type='invoice_payment',
        reference_id=invoice.id
    )
    db.session.add(payment_entry)
    db.session.flush()

    # مدين: البنك
    detail3 = JournalEntryDetail(
        entry_id=payment_entry.id,
        account_id=bank_account.id,
        debit=invoice.amount,
        credit=0,
        description=f'تحصيل قيمة فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail3)

    # دائن: العملاء
    detail4 = JournalEntryDetail(
        entry_id=payment_entry.id,
        account_id=customers.id,
        debit=0,
        credit=invoice.amount,
        description=f'تخفيض رصيد العميل'
    )
    db.session.add(detail4)

    db.session.commit()

    print(f'   ✅ قيد الدفع: {payment_entry.entry_number}')
    print(f'      مدين: البنك (110002): {invoice.amount:,.0f} ريال')
    print(f'      دائن: العملاء (120001): {invoice.amount:,.0f} ريال')

    # ========== 5. عرض أرصدة الحسابات ==========
    print('\n' + '=' * 60)
    print('📊 أرصدة الحسابات بعد إعادة الإنشاء:')
    print('=' * 60)

    customers_balance = customers.get_balance()
    revenue_balance = revenue_account.get_balance()
    bank_balance = bank_account.get_balance()

    print(f'   العملاء (120001): {customers_balance:,.0f} ريال')
    print(f'   إيرادات العقود (410003): {revenue_balance:,.0f} ريال')
    print(f'   البنك (110002): {bank_balance:,.0f} ريال')

    print('\n' + '=' * 60)
    print('✅ تم إعادة إنشاء قيد الفاتورة والدفع بنجاح')
    print('=' * 60)