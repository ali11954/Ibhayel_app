def init_accounts():
    """تهيئة الحسابات المحاسبية الافتراضية"""
    accounts = [
        # الأصول (100000-199999)
        ('110001', 'الصندوق', 'Cash', 'asset', 'debit', None, 1),
        ('110002', 'البنك', 'Bank', 'asset', 'debit', None, 1),
        ('120001', 'المدينون', 'Accounts Receivable', 'asset', 'debit', None, 1),
        ('130001', 'السلف', 'Advances', 'asset', 'debit', None, 1),

        # الخصوم (200000-299999)
        ('210001', 'الرواتب المستحقة', 'Salaries Payable', 'liability', 'credit', None, 1),
        ('210002', 'الإضافي المستحق', 'Overtime Payable', 'liability', 'credit', None, 1),
        ('220001', 'الدائنون', 'Accounts Payable', 'liability', 'credit', None, 1),

        # حقوق الملكية (300000-399999)
        ('310001', 'رأس المال', 'Capital', 'equity', 'credit', None, 1),
        ('320001', 'الأرباح المحتجزة', 'Retained Earnings', 'equity', 'credit', None, 1),

        # الإيرادات (400000-499999)
        ('410001', 'إيرادات الخدمات', 'Service Revenue', 'revenue', 'credit', None, 1),
        ('420001', 'إيرادات أخرى', 'Other Revenue', 'revenue', 'credit', None, 1),

        # المصروفات (500000-599999)
        ('510001', 'مصروف الرواتب', 'Salaries Expense', 'expense', 'debit', None, 1),
        ('510002', 'الخصومات والجزاءات', 'Deductions & Penalties', 'expense', 'debit', None, 1),
        ('510003', 'مصروف الإضافي', 'Overtime Expense', 'expense', 'debit', None, 1),
    ]

    for code, name_ar, name, acc_type, nature, parent_id, level in accounts:
        existing = Account.query.filter_by(code=code).first()
        if not existing:
            account = Account(
                code=code,
                name=name,
                name_ar=name_ar,
                account_type=acc_type,
                nature=nature,
                parent_id=parent_id,
                level=level,
                is_active=True
            )
            db.session.add(account)

    db.session.commit()
    print("✅ تم تهيئة الحسابات المحاسبية الافتراضية")