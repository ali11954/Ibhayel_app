from app import app
from models import db, Account

print('=' * 60)
print('إضافة جميع الحسابات المحاسبية')
print('=' * 60)

accounts = [
    # الأصول (1xxxxx)
    ('110001', 'Cash', 'الصندوق', 'asset', 'debit'),
    ('110002', 'Bank Account', 'البنك', 'asset', 'debit'),
    ('120001', 'Customers', 'العملاء', 'asset', 'debit'),
    ('130001', 'Advances', 'السلف', 'asset', 'debit'),

    # الخصوم (2xxxxx)
    ('210001', 'Salaries Payable', 'الرواتب المستحقة', 'liability', 'credit'),
    ('210002', 'Overtime Payable', 'مستحقات الإضافي', 'liability', 'credit'),
    ('211001', 'Labor Salaries Payable', 'رواتب العمال المستحقة', 'liability', 'credit'),
    ('211002', 'Allowances Payable', 'بدلات العمال المستحقة', 'liability', 'credit'),
    ('211003', 'Insurance Payable', 'تأمينات مستحقة', 'liability', 'credit'),
    ('220001', 'Suppliers', 'الدائنون - موردين', 'liability', 'credit'),
    ('221001', 'Tax Payable', 'ضريبة مستحقة', 'liability', 'credit'),
    ('221002', 'Zakat Payable', 'زكاة مستحقة', 'liability', 'credit'),
    ('230001', 'Accrued Revenue', 'إيرادات مستحقة', 'liability', 'credit'),

    # حقوق الملكية (3xxxxx)
    ('320001', 'Retained Earnings', 'الأرباح المحتجزة', 'equity', 'credit'),

    # الإيرادات (4xxxxx)
    ('410001', 'Annual Contract Revenue', 'إيرادات العقود السنوية', 'revenue', 'credit'),
    ('410002', 'Monthly Contract Revenue', 'إيرادات العقود الشهرية', 'revenue', 'credit'),
    ('410003', 'Quarterly Contract Revenue', 'إيرادات العقود الربع سنوية', 'revenue', 'credit'),
    ('410004', 'Additional Invoices Revenue', 'إيرادات الفواتير الإضافية', 'revenue', 'credit'),

    # المصروفات (5xxxxx)
    ('510001', 'Salaries Expense', 'مصروف الرواتب', 'expense', 'debit'),
    ('510002', 'Deductions Expense', 'مصروف الخصومات والجزاءات', 'expense', 'debit'),
    ('510003', 'Overtime Expense', 'مصروف الإضافي', 'expense', 'debit'),
    ('511001', 'Labor Basic Salary Expense', 'مصروف رواتب العمال الأساسية', 'expense', 'debit'),
    ('511002', 'Labor Resident Allowance Expense', 'مصروف بدل سكن العمال', 'expense', 'debit'),
    ('511003', 'Labor Insurance Expense', 'مصروف تأمين العمال', 'expense', 'debit'),
    ('511004', 'Labor Clothing Expense', 'مصروف بدل ملابس العمال', 'expense', 'debit'),
    ('511005', 'Labor Health Card Expense', 'مصروف بطائق صحية للعمال', 'expense', 'debit'),
    ('520001', 'Company Services Expense', 'مصروف خدمات الشركات', 'expense', 'debit'),
    ('521001', 'Contractor Tax Expense', 'مصروف ضريبة المتعهدين', 'expense', 'debit'),
    ('521002', 'Contractor Zakat Expense', 'مصروف زكاة المتعهدين', 'expense', 'debit'),
    ('530001', 'Utilities Expense', 'كهرباء وماء', 'expense', 'debit'),
    ('530002', 'Rent Expense', 'إيجار', 'expense', 'debit'),
    ('530003', 'Office Supplies', 'مستلزمات مكتبية', 'expense', 'debit'),
    ('530004', 'Equipment Expense', 'معدات وأدوات', 'expense', 'debit'),
    ('530005', 'General Expense', 'مصروفات عامة', 'expense', 'debit'),
]

with app.app_context():
    count = 0
    for code, name, name_ar, acc_type, nature in accounts:
        existing = Account.query.filter_by(code=code).first()
        if not existing:
            account = Account(
                code=code,
                name=name,
                name_ar=name_ar,
                account_type=acc_type,
                nature=nature,
                opening_balance=0,
                is_active=True
            )
            db.session.add(account)
            count += 1
            print(f'  ✅ {code} - {name_ar}')

    db.session.commit()

    print('\n' + '=' * 60)
    print(f'✅ تم إضافة {count} حساب محاسبي جديد')
    if count == 0:
        print('ℹ️ جميع الحسابات موجودة مسبقاً')
    print('=' * 60)