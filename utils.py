# utils.py
from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user
from datetime import datetime, timedelta


def role_required(*roles):
    """محدد الصلاحيات"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('الرجاء تسجيل الدخول أولاً', 'warning')
                return redirect(url_for('login'))
            if current_user.role not in roles and current_user.role != 'admin':
                flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_financial_month_dates(month_year):
    """الحصول على تواريخ الشهر المالي (من 26 إلى 25)"""
    from datetime import datetime

    # تنسيق الإدخال يمكن أن يكون 'MM-YYYY' أو 'YYYY-MM'
    if '-' in month_year:
        parts = month_year.split('-')
        if len(parts[0]) == 4:  # تنسيق YYYY-MM
            year, month = int(parts[0]), int(parts[1])
        else:  # تنسيق MM-YYYY
            month, year = int(parts[0]), int(parts[1])
    else:
        raise ValueError(f"تنسيق غير صحيح للشهر: {month_year}")

    # التحقق من صحة الشهر
    if month < 1 or month > 12:
        raise ValueError(f"الشهر يجب أن يكون بين 1 و 12")

    # تاريخ بداية الشهر المالي (26 من الشهر السابق)
    if month == 1:
        start_date = datetime(year - 1, 12, 26).date()
    else:
        start_date = datetime(year, month - 1, 26).date()

    # تاريخ نهاية الشهر المالي (25 من الشهر الحالي)
    end_date = datetime(year, month, 25).date()

    return start_date, end_date


def format_currency(amount):
    """تنسيق العملة"""
    return f"{amount:,.0f} ر.ي"


def get_regions():
    """الحصول على قائمة المناطق"""
    from models import Employee

    regions = Employee.query.with_entities(Employee.region).filter(
        Employee.region != None,
        Employee.region != ''
    ).distinct().all()
    return [r[0] for r in regions if r[0]]


def get_user_company(user):
    """الحصول على الشركة التابع لها المستخدم"""
    from models import Employee

    if user.role == 'admin':
        return None
    elif user.role == 'supervisor':
        employee = Employee.query.filter_by(user_id=user.id).first()
        return employee.company_id if employee else None
    return None


def filter_by_user_role(query, model, user, company_field='company_id'):
    """تصفية الاستعلام حسب دور المستخدم"""
    if user.role == 'admin':
        return query
    elif user.role == 'supervisor':
        company_id = get_user_company(user)
        if company_id:
            return query.filter(getattr(model, company_field) == company_id)
        return query.filter(False)
    return query.filter(False)


# ==================== دوال مساعدة لاستخراج بيانات الحضور ====================

def get_employee_attendance_summary(employee, start_date, end_date):
    """الحصول على ملخص الحضور للموظف في فترة محددة

    قواعد الاحتساب:
    - الأيام العادية (عدا الجمعة): التسجيل = حضور، عدم التسجيل = غياب
    - يوم الجمعة: فقط إذا تم تسجيل الحضور يحسب، وإذا لم يسجل لا يحسب ولا يعتبر غياب
    """
    from models import Attendance
    from datetime import timedelta

    # جلب سجلات الحضور للموظف في الفترة
    attendances = Attendance.query.filter(
        Attendance.employee_id == employee.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    # تحويل السجلات إلى قاموس للوصول السريع
    attendance_dict = {att.date: att for att in attendances}

    # تهيئة النتائج
    summary = {
        'attendance_days': 0,  # أيام الحضور الفعلية (تحسب في الراتب)
        'absent_days': 0,  # أيام الغياب (تحسب كخصم)
        'sick_days': 0,  # أيام الإجازة المرضية
        'late_minutes_total': 0,  # إجمالي دقائق التأخير
        'friday_attendance_days': 0,  # أيام الجمعة التي تم الحضور فيها
        'total_days': (end_date - start_date).days + 1,  # إجمالي أيام الفترة
        'work_days': 0,  # أيام العمل الفعلية (عدا الجمعة غير المحضورة)
    }

    # المرور على كل يوم في الفترة
    current_date = start_date
    while current_date <= end_date:
        is_friday = current_date.weekday() == 4  # الجمعة = 4

        if current_date in attendance_dict:
            att = attendance_dict[current_date]

            if att.attendance_status == 'present':
                summary['attendance_days'] += 1
                if is_friday:
                    summary['friday_attendance_days'] += 1

            elif att.attendance_status == 'sick':
                summary['sick_days'] += 1
                if is_friday:
                    summary['friday_attendance_days'] += 1

            elif att.attendance_status == 'absent':
                # الغياب المسجل لا يحسب في الجمعة
                if not is_friday:
                    summary['absent_days'] += 1
                else:
                    summary['friday_attendance_days'] += 1  # سجل غياب في الجمعة يعتبر حضور للجمعة

            elif att.attendance_status == 'late':
                summary['attendance_days'] += 1  # المتأخر يعتبر حاضر
                summary['late_minutes_total'] += att.late_minutes or 0
                if is_friday:
                    summary['friday_attendance_days'] += 1
        else:
            # لا يوجد تسجيل لهذا اليوم
            if is_friday:
                # يوم الجمعة بدون تسجيل: لا يحسب ولا يعتبر غياب
                pass
            else:
                # الأيام العادية بدون تسجيل = غياب
                summary['absent_days'] += 1

        current_date += timedelta(days=1)

    # حساب أيام العمل الفعلية (إجمالي الأيام - أيام الجمعة التي لم يحضرها)
    friday_not_attended = summary['total_days'] // 7  # تقدير أولي لعدد أيام الجمعة
    # حساب دقيق لعدد أيام الجمعة في الفترة
    friday_count = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 4:
            friday_count += 1
        current_date += timedelta(days=1)

    # أيام العمل = إجمالي الأيام - أيام الجمعة التي لم يحضرها الموظف
    fridays_attended = summary['friday_attendance_days']
    summary['work_days'] = summary['total_days'] - (friday_count - fridays_attended)

    return summary


def get_employee_daily_allowance(employee, attendance_days):
    """حساب قيمة البدل اليومي"""
    if employee.is_resident:
        daily_rate = getattr(employee, 'daily_allowance', 500)
        return attendance_days * daily_rate
    return 0


def get_employee_advances_sum(employee, start_date=None, end_date=None):
    """الحصول على إجمالي السلف للموظف في الفترة"""
    from models import FinancialTransaction

    query = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == employee.id,
        FinancialTransaction.transaction_type == 'advance',
        FinancialTransaction.is_settled == False
    )

    if start_date and end_date:
        query = query.filter(
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        )

    return sum(t.amount for t in query.all()) or 0


def get_employee_deductions_sum(employee, start_date=None, end_date=None):
    """الحصول على إجمالي الخصومات للموظف في الفترة"""
    from models import FinancialTransaction

    query = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == employee.id,
        FinancialTransaction.transaction_type == 'deduction',
        FinancialTransaction.is_settled == False
    )

    if start_date and end_date:
        query = query.filter(
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        )

    return sum(t.amount for t in query.all()) or 0


def get_employee_penalties_sum(employee, start_date=None, end_date=None):
    """الحصول على إجمالي الجزاءات للموظف في الفترة"""
    from models import FinancialTransaction

    query = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == employee.id,
        FinancialTransaction.transaction_type == 'penalty',
        FinancialTransaction.is_settled == False
    )

    if start_date and end_date:
        query = query.filter(
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date
        )

    return sum(t.amount for t in query.all()) or 0


# ==================== دوال مساعدة لتحضير الدوام ====================

def get_current_month_preparation():
    """الحصول على تحضير الشهر الحالي"""
    try:
        from models import AttendancePreparation
        current_month = datetime.now().strftime('%m-%Y')
        preparation = AttendancePreparation.query.filter_by(
            month_year=current_month
        ).first()
        return preparation
    except Exception as e:
        return None


def get_preparation_by_month(month_year):
    """الحصول على تحضير حسب الشهر"""
    try:
        from models import AttendancePreparation
        preparation = AttendancePreparation.query.filter_by(
            month_year=month_year
        ).first()
        return preparation
    except Exception as e:
        return None


def check_can_calculate_salary(month_year):
    """التحقق من إمكانية حساب الراتب للشهر"""
    try:
        from models import AttendancePreparation
        preparation = AttendancePreparation.query.filter_by(
            month_year=month_year
        ).first()

        if preparation and not preparation.is_processed:
            return False, "يجب أولاً تصفية وترحيل تحضير الدوام"

        return True, None
    except:
        return True, None


# ==================== سياق القالب (Template Context) ====================

def inject_template_globals():
    """إضافة دوال مساعدة لجميع القوالب"""
    return dict(
        get_current_month_preparation=get_current_month_preparation,
        format_currency=format_currency,
        now=datetime.now()
    )


# ==================== دوال مساعدة للفلترة في القوالب ====================

def get_status_badge_class(status):
    """الحصول على كلاس CSS لحالة معينة"""
    badges = {
        'present': 'success',
        'absent': 'danger',
        'late': 'warning',
        'sick': 'info',
        'paid': 'success',
        'unpaid': 'danger',
        'active': 'success',
        'inactive': 'secondary',
        'completed': 'info',
        'pending': 'warning',
        'transferred': 'primary',
        'processed': 'success',
        'approved': 'success',
        'rejected': 'danger'
    }
    return badges.get(status, 'secondary')


def get_status_text_ar(status):
    """الحصول على النص العربي للحالة"""
    texts = {
        'present': 'حاضر',
        'absent': 'غائب',
        'late': 'متأخر',
        'sick': 'إجازة مرضية',
        'paid': 'مدفوع',
        'unpaid': 'غير مدفوع',
        'active': 'نشط',
        'inactive': 'غير نشط',
        'completed': 'مكتمل',
        'pending': 'قيد الانتظار',
        'transferred': 'تم الترحيل',
        'processed': 'تمت المعالجة',
        'approved': 'معتمد',
        'rejected': 'مرفوض'
    }
    return texts.get(status, status)


# ==================== دوال مساعدة للتنسيق ====================

def format_date_ar(date):
    """تنسيق التاريخ بالعربية"""
    if not date:
        return ''

    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
        5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
        9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }

    return f"{date.day} {months_ar[date.month]} {date.year}"


def format_percentage(value, decimals=1):
    """تنسيق النسبة المئوية"""
    return f"{value:.{decimals}f}%"


def get_rating_class(score):
    """الحصول على كلاس CSS حسب درجة التقييم"""
    if score >= 90:
        return 'success'
    elif score >= 75:
        return 'info'
    elif score >= 60:
        return 'warning'
    else:
        return 'danger'


def get_rating_text(score):
    """الحصول على نص التقييم حسب الدرجة"""
    if score >= 90:
        return 'ممتاز'
    elif score >= 75:
        return 'جيد جداً'
    elif score >= 60:
        return 'جيد'
    elif score >= 50:
        return 'مقبول'
    else:
        return 'ضعيف'


# ==================== دوال المحاسبة ====================
def create_journal_entry(date, description, entries, reference_type=None, reference_id=None):
    """
    إنشاء قيد يومي جديد

    Args:
        date: تاريخ القيد
        description: وصف القيد
        entries: قائمة من tuples (account_id, debit, credit, description)
        reference_type: نوع المرجع
        reference_id: معرف المرجع
    """
    from models import JournalEntry, JournalEntryDetail, db
    from flask_login import current_user
    from datetime import datetime

    # التحقق من صحة المدخلات
    if not entries:
        raise ValueError("لا توجد تفاصيل للقيد")

    total_debit = sum(d[1] for d in entries)
    total_credit = sum(d[2] for d in entries)

    if abs(total_debit - total_credit) > 0.01:
        raise ValueError(f"القيد غير متوازن: مدين={total_debit}, دائن={total_credit}")

    # إنشاء رقم القيد
    entry_number = get_next_entry_number()

    # إنشاء القيد الرئيسي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد
    for account_id, debit, credit, entry_description in entries:
        if debit == 0 and credit == 0:
            continue

        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=account_id,
            debit=debit,
            credit=credit,
            description=entry_description
        )
        db.session.add(detail)

    db.session.commit()

    # تحديث أرصدة الحسابات (تحديث فوري)
    for account_id, debit, credit, _ in entries:
        account = db.session.get(Account, account_id)
        if account:
            # تحديث الرصيد في الكائن (سيتم حسابه عند الطلب)
            db.session.expire(account, ['balances'])

    return journal_entry


def generate_supplier_invoice_number():
    """توليد رقم فاتورة مورد تلقائي"""
    from datetime import datetime

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

    return f"SI-{date_str}-{str(new_num).zfill(3)}"


def auto_close_expenses():
    """
    إقفال حسابات المصروفات تلقائياً وترحيلها إلى الأرباح المحتجزة
    مع تفصيل كل مصروف على حدة
    """
    from models import Account, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from flask_login import current_user

    # الحصول على حسابات المصروفات (باستثناء حساب المصروفات العامة)
    expense_accounts = Account.query.filter(
        Account.account_type == 'expense',
        Account.is_active == True,
        Account.code != '530005'  # استثناء المصروفات العامة
    ).all()

    # إضافة حساب المصروفات العامة إذا كان له رصيد
    general_expense = Account.query.filter_by(code='530005').first()
    if general_expense and general_expense.get_balance() != 0:
        expense_accounts.append(general_expense)

    retained_earnings = Account.query.filter_by(code='320001').first()

    if not retained_earnings:
        retained_earnings = Account(
            code='320001',
            name='Retained Earnings',
            name_ar='الأرباح المحتجزة',
            account_type='equity',
            nature='credit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(retained_earnings)
        db.session.commit()

    total_expenses = 0
    expenses_to_close = []

    for expense in expense_accounts:
        balance = expense.get_balance()
        if balance != 0:
            total_expenses += balance
            expenses_to_close.append({
                'account': expense,
                'balance': balance,
                'name': expense.name_ar,
                'code': expense.code
            })

    if total_expenses == 0:
        print("✅ لا توجد مصروفات للإقفال")
        return None

    # التحقق من عدم وجود قيد إقفال سابق
    current_month = datetime.now().strftime('%Y-%m')
    existing = JournalEntry.query.filter(
        JournalEntry.reference_type == 'closing_expenses',
        JournalEntry.description.like(f'%{current_month}%')
    ).first()

    if existing:
        print(f"⚠️ يوجد قيد إقفال للشهر {current_month} بالفعل: {existing.entry_number}")
        return existing

    # إنشاء قيد الإقفال
    from utils import get_next_entry_number
    entry_number = get_next_entry_number()

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'إقفال حسابات المصروفات وترحيلها إلى الأرباح المحتجزة - {datetime.now().strftime("%B %Y")}',
        reference_type='closing_expenses',
        reference_id=None,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: الأرباح المحتجزة
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=retained_earnings.id,
        debit=total_expenses,
        credit=0,
        description=f'ترحيل إجمالي المصروفات ({total_expenses:,.2f})'
    )
    db.session.add(detail1)

    # إقفال كل حساب مصروف على حدة مع تفصيل
    for exp in expenses_to_close:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=exp['account'].id,
            debit=0,
            credit=exp['balance'],
            description=f'إقفال حساب {exp["name"]} ({exp["code"]}) - {exp["balance"]:,.2f}'
        )
        db.session.add(detail)
        print(f"   ✅ تم إقفال {exp['name']}: {exp['balance']:,.2f}")

    db.session.commit()

    print(f"\n✅ تم إنشاء قيد إقفال المصروفات: {entry_number}")
    print(f"💰 تم ترحيل {total_expenses:,.2f} ريال إلى الأرباح المحتجزة")
    print(f"📋 عدد المصروفات المقفلة: {len(expenses_to_close)}")

    return journal_entry


def redistribute_expenses():
    """
    إعادة توزيع المصروفات العامة إلى حساباتها الصحيحة
    يتم استخدامها عندما يتم تجميع المصروفات في حساب واحد
    """
    from models import Account, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from utils import get_next_entry_number

    general_expense = Account.query.filter_by(code='530005').first()
    if not general_expense:
        return {'success': False, 'message': 'حساب المصروفات العامة غير موجود'}

    current_balance = general_expense.get_balance()
    if current_balance == 0:
        return {'success': False, 'message': 'لا توجد مبالغ في المصروفات العامة لإعادة توزيعها'}

    # هنا يمكنك تحديد المبالغ الصحيحة لكل حساب
    # هذا مثال، يمكن تعديله حسب احتياجاتك
    expense_distribution = {
        '530001': {'name': 'كهرباء وماء', 'amount': 0},
        '530002': {'name': 'إيجار', 'amount': 0},
        '530003': {'name': 'مستلزمات مكتبية', 'amount': 0},
        '530004': {'name': 'معدات وأدوات', 'amount': 0},
    }

    # إنشاء قيد إعادة التوزيع
    entry_number = get_next_entry_number()

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'إعادة توزيع المصروفات العامة إلى حساباتها الصحيحة',
        reference_type='expense_reallocation',
        reference_id=None,
        created_by=1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # دائن: مصروفات عامة (تخفيض)
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=general_expense.id,
        debit=0,
        credit=current_balance,
        description=f'نقل من المصروفات العامة ({current_balance:,.2f})'
    )
    db.session.add(detail1)

    distributed = 0
    for code, data in expense_distribution.items():
        if data['amount'] > 0:
            expense_account = Account.query.filter_by(code=code).first()
            if expense_account:
                detail = JournalEntryDetail(
                    entry_id=journal_entry.id,
                    account_id=expense_account.id,
                    debit=data['amount'],
                    credit=0,
                    description=f'تسجيل مصروف {data["name"]}'
                )
                db.session.add(detail)
                distributed += data['amount']

    # إذا لم يتم توزيع المبلغ بالكامل، الباقي يبقى في المصروفات العامة
    if distributed < current_balance:
        remaining = current_balance - distributed
        detail_remaining = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=general_expense.id,
            debit=remaining,
            credit=0,
            description=f'المبلغ المتبقي في المصروفات العامة'
        )
        db.session.add(detail_remaining)

    db.session.commit()

    return {
        'success': True,
        'message': f'تم إعادة توزيع {current_balance:,.2f} ريال',
        'entry_number': entry_number,
        'distributed': distributed,
        'remaining': current_balance - distributed
    }

def refresh_all_reports():
    """تحديث جميع التقارير بعد أي عملية"""
    from models import Account

    # تحديث أرصدة الحسابات
    accounts = Account.query.all()
    for account in accounts:
        db.session.expire(account, ['balances'])

    db.session.commit()
    print("✅ تم تحديث جميع أرصدة الحسابات")


def create_salary_accrual(salary):
    """إنشاء قيد استحقاق الراتب (يتم عند حساب الراتب)"""
    journal_entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=salary.created_at.date(),
        description=f'استحقاق راتب {salary.employee.name} عن {salary.notes}',
        reference_type='salary_accrual',
        reference_id=salary.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: مصروف الرواتب
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=salary_expense.id,  # حساب 510001
        debit=salary.total_salary,
        credit=0,
        description=f'راتب {salary.employee.name}'
    )

    # دائن: الرواتب المستحقة
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=salaries_payable.id,  # حساب 210001
        debit=0,
        credit=salary.total_salary,
        description=f'استحقاق راتب {salary.employee.name}'
    )
def create_salary_journal_entry(salary):
    """
    إنشاء قيد محاسبي للراتب (عند استحقاق الراتب)

    المدين: مصروف الرواتب (510001)
    الدائن: الرواتب المستحقة (210001)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account
    from datetime import datetime

    # البحث عن حساب مصروف الرواتب
    salary_expense = Account.query.filter_by(code='510001').first()
    if not salary_expense:
        salary_expense = Account(
            code='510001',
            name='Salaries Expense',
            name_ar='مصروف الرواتب',
            account_type='expense',
            nature='debit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(salary_expense)
        db.session.commit()

    # البحث عن حساب الرواتب المستحقة
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

    # إنشاء رقم قيد فريد
    last_entry = JournalEntry.query.order_by(JournalEntry.entry_number.desc()).first()
    if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JE-'):
        try:
            last_num = int(last_entry.entry_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1

    entry_number = f"JE-{datetime.now().year}-{str(new_num).zfill(5)}"

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'استحقاق راتب {salary.employee.name} عن {salary.notes}',
        reference_type='salary',
        reference_id=salary.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # ✅ استخدام entry_id (وليس journal_entry_id)
    # مدين: مصروف الرواتب
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,  # ✅ العمود الصحيح
        account_id=salary_expense.id,
        debit=salary.total_salary,
        credit=0,
        description=f'راتب {salary.employee.name}'
    )
    db.session.add(detail1)

    # دائن: الرواتب المستحقة
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,  # ✅ العمود الصحيح
        account_id=salaries_payable.id,
        debit=0,
        credit=salary.total_salary,
        description=f'استحقاق راتب {salary.employee.name}'
    )
    db.session.add(detail2)

    db.session.commit()

    # ربط القيد بالراتب
    salary.journal_entry_id = journal_entry.id
    db.session.commit()

    return journal_entry

def create_transaction_journal_entry(transaction):
    """إنشاء قيد محاسبي للمعاملة المالية"""
    from models import Account

    if transaction.transaction_type == 'advance':
        # سلفة: من حساب السلف (أصل) إلى حساب الصندوق (أصل) أو العكس
        advance_account = Account.query.filter_by(code='130001').first()  # السلف
        cash_account = Account.query.filter_by(code='110001').first()  # الصندوق

        if not advance_account or not cash_account:
            raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

        entries = [
            (advance_account.id, transaction.amount, 0, f'سلفة {transaction.employee.name}'),
            (cash_account.id, 0, transaction.amount, f'صرف سلفة')
        ]
    elif transaction.transaction_type == 'overtime':
        # إضافي: من مصروف الإضافي إلى حساب المستحق
        overtime_account = Account.query.filter_by(code='510003').first()  # مصروف الإضافي
        payable_account = Account.query.filter_by(code='210002').first()  # مستحقات الإضافي

        if not overtime_account or not payable_account:
            raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

        entries = [
            (overtime_account.id, transaction.amount, 0, f'إضافي {transaction.employee.name}'),
            (payable_account.id, 0, transaction.amount, f'استحقاق إضافي')
        ]
    elif transaction.transaction_type == 'deduction':
        # خصم: من حساب المستحق إلى حساب الخصومات
        payable_account = Account.query.filter_by(code='210001').first()  # الرواتب المستحقة
        deduction_account = Account.query.filter_by(code='510002').first()  # الخصومات

        if not payable_account or not deduction_account:
            raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

        entries = [
            (payable_account.id, transaction.amount, 0, f'خصم من راتب {transaction.employee.name}'),
            (deduction_account.id, 0, transaction.amount, f'تسجيل خصم')
        ]
    elif transaction.transaction_type == 'penalty':
        # جزاء: من حساب المستحق إلى حساب الجزاءات
        payable_account = Account.query.filter_by(code='210001').first()  # الرواتب المستحقة
        penalty_account = Account.query.filter_by(code='510002').first()  # الخصومات والجزاءات

        if not payable_account or not penalty_account:
            raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

        entries = [
            (payable_account.id, transaction.amount, 0, f'جزاء على {transaction.employee.name}'),
            (penalty_account.id, 0, transaction.amount, f'تسجيل جزاء')
        ]
    else:
        return None

    return create_journal_entry(
        date=transaction.date,
        description=f'{transaction.get_type_name()} للموظف {transaction.employee.name}',
        entries=entries,
        reference_type='transaction',
        reference_id=transaction.id
    )

def create_invoice_journal_entry(invoice):
    """إنشاء قيد محاسبي للفاتورة"""
    from models import Account

    # ✅ استخدام الأكواد الصحيحة
    receivable_account = Account.query.filter_by(code='120001').first()  # العملاء
    revenue_account = Account.query.filter_by(code='410004').first()  # إيرادات الفواتير الإضافية

    if not receivable_account or not revenue_account:
        # محاولة إنشاء الحسابات إذا لم تكن موجودة
        if not receivable_account:
            receivable_account = Account(
                code='120001',
                name='Customers',
                name_ar='العملاء',
                account_type='asset',
                nature='debit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(receivable_account)
        if not revenue_account:
            revenue_account = Account(
                code='410004',
                name='Additional Invoices Revenue',
                name_ar='إيرادات الفواتير الإضافية',
                account_type='revenue',
                nature='credit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(revenue_account)
        db.session.commit()

    entries = [
        (receivable_account.id, invoice.amount, 0, f'فاتورة رقم {invoice.invoice_number}'),
        (revenue_account.id, 0, invoice.amount, f'إيرادات فاتورة {invoice.invoice_number}')
    ]

    return create_journal_entry(
        date=invoice.invoice_date,
        description=f'فاتورة رقم {invoice.invoice_number} - {invoice.contract.company.name if invoice.contract else ""}',
        entries=entries,
        reference_type='invoice',
        reference_id=invoice.id
    )

def create_invoice_payment_journal_entry(invoice, paid_amount, payment_method):
    """إنشاء قيد محاسبي لتسديد فاتورة"""
    from models import Account

    bank_account = Account.query.filter_by(code='110002').first()  # البنك
    receivable_account = Account.query.filter_by(code='120001').first()  # المدينون

    if not bank_account or not receivable_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    entries = [
        (bank_account.id, paid_amount, 0, f'تسديد فاتورة {invoice.invoice_number}'),
        (receivable_account.id, 0, paid_amount, f'تحصيل قيمة فاتورة {invoice.invoice_number}')
    ]

    return create_journal_entry(
        date=datetime.now().date(),
        description=f'تسديد فاتورة رقم {invoice.invoice_number} - طريقة الدفع: {payment_method}',
        entries=entries,
        reference_type='invoice_payment',
        reference_id=invoice.id
    )


def create_salary_payment_journal_entry(salary):
    """إنشاء قيد محاسبي لصرف الراتب"""
    from models import Account, JournalEntry, JournalEntryDetail, db
    from flask_login import current_user
    from datetime import datetime

    # البحث عن الحسابات
    payable_account = Account.query.filter_by(code='210001').first()
    bank_account = Account.query.filter_by(code='110002').first()

    if not payable_account or not bank_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    # استخدام الدالة الجديدة للحصول على رقم القيد
    entry_number = get_next_entry_number()

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=salary.paid_date or datetime.now().date(),
        description=f'صرف راتب {salary.employee.name} عن {salary.notes}',
        reference_type='salary_payment',
        reference_id=salary.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: الرواتب المستحقة
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=payable_account.id,
        debit=salary.total_salary,
        credit=0,
        description=f'صرف راتب {salary.employee.name}'
    )
    db.session.add(detail1)

    # دائن: البنك
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=bank_account.id,
        debit=0,
        credit=salary.total_salary,
        description=f'دفع الراتب عبر {salary.payment_method}'
    )
    db.session.add(detail2)

    db.session.commit()
    return journal_entry


def create_company_payment_journal_entry(payment):
    """إنشاء قيد محاسبي لدفع مبلغ لشركة (مصروف)"""
    from models import Account

    # حساب المصروفات (مصروف خدمات / مصروف مشتريات)
    expense_account = Account.query.filter_by(code='520001').first()  # مصروف خدمات الشركات

    # حساب البنك أو الصندوق
    if payment.payment_method == 'cash':
        bank_account = Account.query.filter_by(code='110001').first()  # الصندوق
    else:
        bank_account = Account.query.filter_by(code='110002').first()  # البنك

    if not expense_account or not bank_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    entries = [
        (expense_account.id, payment.amount, 0, f'دفع لشركة {payment.company.name}'),
        (bank_account.id, 0, payment.amount, f'تسديد مستحقات شركة {payment.company.name}')
    ]

    return create_journal_entry(
        date=payment.payment_date,
        description=f'دفع مستحقات للشركة {payment.company.name} - {payment.reference_number or ""}',
        entries=entries,
        reference_type='company_payment',
        reference_id=payment.id
    )


def create_supplier_invoice_journal_entry(invoice):
    """إنشاء قيد محاسبي لفاتورة واردة من مورد"""
    from models import Account, JournalEntry, JournalEntryDetail, db
    from flask_login import current_user

    # حساب المصروفات حسب الفئة
    expense_accounts = {
        'utilities': '530001',  # كهرباء وماء
        'rent': '530002',  # إيجار
        'office': '530003',  # مستلزمات مكتبية
        'equipment': '530004',  # معدات وأدوات
        'general': '530005'  # مصروفات عامة
    }

    # تحديد الحساب بناءً على فئة المصروف
    category_name = invoice.category.name if invoice.category else 'general'
    account_code = expense_accounts.get(category_name, '530005')

    expense_account = Account.query.filter_by(code=account_code).first()
    payable_account = Account.query.filter_by(code='220001').first()  # الدائنون

    if not expense_account or not payable_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    # إنشاء رقم القيد
    year = invoice.invoice_date.strftime('%Y')
    count = JournalEntry.query.filter(JournalEntry.date >= f'{year}-01-01').count() + 1
    entry_number = f'JE-{year}-{str(count).zfill(5)}'

    # وصف القيد
    description = f'فاتورة واردة من {invoice.supplier.name_ar} - {invoice.category.name_ar if invoice.category else "مصروفات"}'

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=invoice.invoice_date,
        description=description,
        reference_type='supplier_invoice',
        reference_id=invoice.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد (مدين للمصروفات، دائن للدائنون)
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=expense_account.id,
        debit=invoice.amount,
        credit=0,
        description=f'فاتورة {invoice.invoice_number} - {invoice.supplier.name_ar}'
    )
    db.session.add(detail1)

    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=payable_account.id,
        debit=0,
        credit=invoice.amount,
        description=f'استحقاق فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail2)

    db.session.commit()
    return journal_entry


def create_supplier_invoice_payment_journal_entry(invoice, payment_amount, payment_method):
    """إنشاء قيد محاسبي لتسديد فاتورة مورد"""
    from models import Account, JournalEntry, JournalEntryDetail, db
    from flask_login import current_user

    payable_account = Account.query.filter_by(code='220001').first()  # الدائنون

    if payment_method == 'cash':
        bank_account = Account.query.filter_by(code='110001').first()  # الصندوق
    else:
        bank_account = Account.query.filter_by(code='110002').first()  # البنك

    if not payable_account or not bank_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    # إنشاء رقم القيد
    today = datetime.now().date()
    year = today.strftime('%Y')
    count = JournalEntry.query.filter(JournalEntry.date >= f'{year}-01-01').count() + 1
    entry_number = f'JE-{year}-{str(count).zfill(5)}'

    description = f'تسديد فاتورة مورد رقم {invoice.invoice_number} - {invoice.supplier.name_ar}'

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=today,
        description=description,
        reference_type='supplier_payment',
        reference_id=invoice.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد (مدين للدائنون، دائن للصندوق/البنك)
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=payable_account.id,
        debit=payment_amount,
        credit=0,
        description=f'تسديد فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail1)

    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=bank_account.id,
        debit=0,
        credit=payment_amount,
        description=f'دفع مستحقات {invoice.supplier.name_ar}'
    )
    db.session.add(detail2)

    db.session.commit()
    return journal_entry

def create_expense_invoice_journal_entry(invoice):
    """إنشاء قيد محاسبي لفاتورة مصروف واردة"""
    from models import Account

    # تحديد الحساب حسب الفئة
    expense_accounts = {
        'utility': '530001',  # كهرباء وماء
        'rent': '530002',  # إيجار
        'office': '530003',  # مستلزمات مكتبية
        'equipment': '530004',  # معدات وأدوات
        'general': '530005'  # مصروفات عامة
    }

    account_code = expense_accounts.get(invoice.category.name, '530005')
    expense_account = Account.query.filter_by(code=account_code).first()
    payable_account = Account.query.filter_by(code='220001').first()  # الدائنون

    if not expense_account or not payable_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    entries = [
        (expense_account.id, invoice.amount, 0, f'فاتورة {invoice.invoice_number} - {invoice.supplier.name}'),
        (payable_account.id, 0, invoice.amount, f'استحقاق فاتورة {invoice.invoice_number}')
    ]

    return create_journal_entry(
        date=invoice.invoice_date,
        description=f'فاتورة واردة من {invoice.supplier.name} - {invoice.category.name_ar}',
        entries=entries,
        reference_type='expense_invoice',
        reference_id=invoice.id
    )


def create_expense_payment_journal_entry(payment):
    """إنشاء قيد محاسبي لدفع مصروف"""
    from models import Account

    payable_account = Account.query.filter_by(code='220001').first()  # الدائنون

    if payment.payment_method == 'cash':
        bank_account = Account.query.filter_by(code='110001').first()  # الصندوق
    else:
        bank_account = Account.query.filter_by(code='110002').first()  # البنك

    if not payable_account or not bank_account:
        raise ValueError("الحسابات المحاسبية غير مهيأة بشكل صحيح")

    entries = [
        (payable_account.id, payment.amount, 0, f'تسديد فاتورة {payment.invoice.invoice_number}'),
        (bank_account.id, 0, payment.amount, f'دفع مستحقات {payment.invoice.supplier.name}')
    ]

    return create_journal_entry(
        date=payment.payment_date,
        description=f'تسديد فاتورة {payment.invoice.invoice_number} - {payment.invoice.supplier.name}',
        entries=entries,
        reference_type='expense_payment',
        reference_id=payment.id
    )


def reverse_journal_entry(journal_entry_id):
    """عكس قيد محاسبي (إنشاء قيد عكسي)"""
    from models import JournalEntry, JournalEntryDetail, db
    from flask_login import current_user
    from datetime import datetime

    original_entry = JournalEntry.query.get(journal_entry_id)
    if not original_entry:
        raise ValueError("القيد المحاسبي غير موجود")

    # التحقق من عدم وجود قيد عكسي مسبق
    existing_reverse = JournalEntry.query.filter(
        JournalEntry.reference_type == 'reverse',
        JournalEntry.reference_id == original_entry.id
    ).first()

    if existing_reverse:
        raise ValueError(f"يوجد قيد عكسي مسبق: {existing_reverse.entry_number}")

    # إنشاء رقم القيد العكسي
    entry_number = get_next_entry_number()

    # إنشاء قيد عكسي
    reverse_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'عكس قيد: {original_entry.entry_number} - {original_entry.description[:80]}',
        reference_type='reverse',
        reference_id=original_entry.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(reverse_entry)
    db.session.flush()

    # عكس تفاصيل القيد (تبديل المدين والدائن)
    for detail in original_entry.details:
        reverse_detail = JournalEntryDetail(
            entry_id=reverse_entry.id,
            account_id=detail.account_id,
            debit=detail.credit,  # عكس: الدائن يصبح مدين
            credit=detail.debit,  # عكس: المدين يصبح دائن
            description=f'عكس: {detail.description} (قيد أصلي: {original_entry.entry_number})'
        )
        db.session.add(reverse_detail)

    db.session.commit()
    return reverse_entry

def reverse_invoice_journal_entry(invoice):
    """عكس القيد المحاسبي للفاتورة"""
    if not invoice.has_journal_entry():
        raise ValueError("لا يوجد قيد محاسبي لهذه الفاتورة")

    # عكس القيد الأصلي
    reverse_entry = reverse_journal_entry(invoice.journal_entry_id)

    # تحديث الفاتورة
    invoice.journal_entry_id = None
    invoice.is_paid = False
    invoice.paid_amount = 0
    invoice.paid_date = None

    return reverse_entry


def get_employee_overtime_hours(employee, start_date, end_date):
    """الحصول على ساعات العمل الإضافي في الفترة (تحويل المبالغ إلى ساعات)"""
    from models import FinancialTransaction

    overtime_trans = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == employee.id,
        FinancialTransaction.transaction_type == 'overtime',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date,
        FinancialTransaction.is_settled == False
    ).all()

    # حساب الأجر بالساعة
    hourly_rate = employee.salary / 30 / 8

    total_hours = 0
    for t in overtime_trans:
        if t.amount > 1000:  # مبلغ كبير -> نحوله إلى ساعات
            hours = t.amount / (hourly_rate * 1.5)
            total_hours += hours
        else:  # قيمة صغيرة -> قد تكون ساعات بالفعل
            total_hours += t.amount

    return round(total_hours, 1)  # تقريب إلى أقرب 0.5 ساعة


# ==================== دوال القيود المحاسبية للعقود والفواتير (إضافية) ====================
def create_contract_journal_entry(contract, month_date=None):
    """
    إنشاء قيد محاسبي للعقد (عند استحقاق القسط الشهري)

    المدين: العملاء (120001)
    الدائن: حساب الإيرادات حسب نوع العقد:
        - annual: إيرادات العقود السنوية (410001)
        - monthly: إيرادات العقود الشهرية (410002)
        - quarterly: إيرادات العقود الربع سنوية (410003)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account
    from datetime import datetime
    from flask_login import current_user

    # الحصول على حسابات العملاء
    customers = Account.query.filter_by(code='120001').first()
    if not customers:
        customers = Account(
            code='120001',
            name='Customers',
            name_ar='العملاء',
            account_type='asset',
            nature='debit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(customers)
        db.session.commit()

    # تحديد حساب الإيرادات حسب نوع العقد
    if contract.contract_type == 'annual':
        # ✅ استخدام الحساب الصحيح للعقود السنوية
        revenue_account = Account.query.filter_by(code='410001').first()
        if not revenue_account:
            revenue_account = Account(
                code='410001',
                name='Annual Contract Revenue',
                name_ar='إيرادات العقود السنوية',
                account_type='revenue',
                nature='credit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(revenue_account)
        monthly_amount = contract.contract_value / 12
        revenue_type = 'annual'

    elif contract.contract_type == 'monthly':
        # ✅ استخدام الحساب الصحيح للعقود الشهرية
        revenue_account = Account.query.filter_by(code='410002').first()
        if not revenue_account:
            revenue_account = Account(
                code='410002',
                name='Monthly Contract Revenue',
                name_ar='إيرادات العقود الشهرية',
                account_type='revenue',
                nature='credit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(revenue_account)
        monthly_amount = contract.contract_value
        revenue_type = 'monthly'

    elif contract.contract_type == 'quarterly':
        # ✅ استخدام الحساب الصحيح للعقود الربع سنوية
        revenue_account = Account.query.filter_by(code='410003').first()
        if not revenue_account:
            revenue_account = Account(
                code='410003',
                name='Quarterly Contract Revenue',
                name_ar='إيرادات العقود الربع سنوية',
                account_type='revenue',
                nature='credit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(revenue_account)
        monthly_amount = contract.contract_value / 3
        revenue_type = 'quarterly'
    else:
        # افتراضي: إيرادات الخدمات
        revenue_account = Account.query.filter_by(code='410001').first()
        monthly_amount = contract.contract_value
        revenue_type = 'service'

    db.session.commit()

    # تاريخ القيد
    if month_date:
        entry_date = month_date
    else:
        entry_date = datetime.now().date()

    # التحقق من عدم وجود قيد مسبق لنفس الشهر والعقد
    month_str = entry_date.strftime('%Y-%m')
    existing = JournalEntry.query.filter(
        JournalEntry.reference_type == 'contract',
        JournalEntry.reference_id == contract.id,
        JournalEntry.description.like(f'%{month_str}%')
    ).first()

    if existing:
        print(f"⚠️ يوجد قيد مسبق للعقد {contract.id} للشهر {month_str}")
        return existing

    # إنشاء رقم قيد فريد
    entry_number = get_next_entry_number()

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=entry_date,
        description=f'قسط عقد {revenue_type} - شركة {contract.company.name} - {entry_date.strftime("%B %Y")}',
        reference_type='contract',
        reference_id=contract.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: العملاء
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=customers.id,
        debit=monthly_amount,
        credit=0,
        description=f'قسط عقد {contract.company.name} لشهر {entry_date.strftime("%B")}'
    )
    db.session.add(detail1)

    # دائن: حساب الإيرادات حسب نوع العقد
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=revenue_account.id,
        debit=0,
        credit=monthly_amount,
        description=f'إيرادات عقد {contract.company.name}'
    )
    db.session.add(detail2)

    db.session.commit()

    print(f"✅ تم إنشاء قيد محاسبي للعقد {contract.id} ({contract.company.name}): {monthly_amount:,.2f} ريال")
    print(f"   الحساب الدائن: {revenue_account.code} - {revenue_account.name_ar}")
    return journal_entry


def fix_contract_revenue_accounts():
    """
    تصحيح الأرصدة: نقل إيرادات العقود من حساب إيرادات الخدمات (410001)
    إلى الحسابات الصحيحة حسب نوع العقد
    """
    from models import db, Account, JournalEntry, JournalEntryDetail, Contract
    from datetime import datetime
    from utils import get_next_entry_number

    # الحسابات
    service_revenue = Account.query.filter_by(code='410001').first()
    monthly_revenue = Account.query.filter_by(code='410002').first()
    quarterly_revenue = Account.query.filter_by(code='410003').first()

    if not service_revenue:
        print("❌ حساب إيرادات الخدمات غير موجود")
        return

    # جلب جميع العقود
    contracts = Contract.query.all()

    print("\n🔍 تصحيح أرصدة العقود:")
    print("=" * 50)

    for contract in contracts:
        # تحديد الحساب الصحيح حسب نوع العقد
        if contract.contract_type == 'annual':
            correct_account = Account.query.filter_by(code='410001').first()
            account_name = "إيرادات العقود السنوية"
        elif contract.contract_type == 'monthly':
            correct_account = monthly_revenue
            account_name = "إيرادات العقود الشهرية"
        elif contract.contract_type == 'quarterly':
            correct_account = quarterly_revenue
            account_name = "إيرادات العقود الربع سنوية"
        else:
            continue

        if not correct_account:
            print(f"⚠️ الحساب {account_name} غير موجود، يتم إنشاؤه...")
            correct_account = Account(
                code='410002' if contract.contract_type == 'monthly' else '410003',
                name=f'{contract.contract_type.title()} Contract Revenue',
                name_ar=account_name,
                account_type='revenue',
                nature='credit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(correct_account)
            db.session.commit()

        # البحث عن قيود العقد
        contract_entries = JournalEntry.query.filter(
            JournalEntry.reference_type == 'contract',
            JournalEntry.reference_id == contract.id
        ).all()

        for entry in contract_entries:
            # التحقق من أن القيد يستخدم الحساب الخطأ
            for detail in entry.details:
                if detail.account_id == service_revenue.id and detail.credit > 0:
                    print(f"\n📌 تصحيح القيد: {entry.entry_number}")
                    print(f"   العقد: {contract.company.name} ({contract.contract_type})")
                    print(f"   المبلغ: {detail.credit:,.2f} ريال")
                    print(f"   من: إيرادات الخدمات (410001)")
                    print(f"   إلى: {account_name} ({correct_account.code})")

                    # تعديل القيد
                    detail.account_id = correct_account.id
                    detail.description = f'إيرادات عقد {contract.company.name} (مصحح)'

        db.session.commit()

    print("\n✅ تم تصحيح جميع القيود")

def create_customer_invoice_journal_entry(invoice):
    """
    إنشاء قيد محاسبي لفاتورة عميل (إضافية خارج العقود)

    المدين: العملاء (120001)
    الدائن: إيرادات فواتير إضافية (410004)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account
    from flask_login import current_user

    # الحصول على حسابات العملاء
    customers = Account.query.filter_by(code='120001').first()
    if not customers:
        customers = Account(
            code='120001',
            name='Customers',
            name_ar='العملاء',
            account_type='asset',
            nature='debit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(customers)
        db.session.commit()

    # حساب الإيرادات الإضافية
    revenue_account = Account.query.filter_by(code='410004').first()
    if not revenue_account:
        revenue_account = Account(
            code='410004',
            name='Additional Invoices Revenue',
            name_ar='إيرادات الفواتير الإضافية',
            account_type='revenue',
            nature='credit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(revenue_account)
        db.session.commit()

    # التحقق من وجود قيد مسبق
    if invoice.journal_entry_id:
        print(f"⚠️ الفاتورة {invoice.invoice_number} لها قيد مسبق")
        return None

    # إنشاء رقم قيد فريد
    last_entry = JournalEntry.query.order_by(JournalEntry.entry_number.desc()).first()
    if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JE-'):
        try:
            last_num = int(last_entry.entry_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1

    entry_number = f"JE-{invoice.invoice_date.year}-{str(new_num).zfill(5)}"

    # وصف الفاتورة
    company_name = invoice.contract.company.name if invoice.contract and invoice.contract.company else "عميل"

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=invoice.invoice_date,
        description=f'فاتورة {invoice.invoice_number} - {company_name}',
        reference_type='customer_invoice',
        reference_id=invoice.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد
    # مدين: العملاء
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=customers.id,
        debit=invoice.amount,
        credit=0,
        description=f'فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail1)

    # دائن: إيرادات الفواتير الإضافية
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=revenue_account.id,
        debit=0,
        credit=invoice.amount,
        description=f'إيرادات فاتورة {invoice.invoice_number}'
    )
    db.session.add(detail2)

    db.session.commit()

    # ربط القيد بالفاتورة
    invoice.journal_entry_id = journal_entry.id
    db.session.commit()

    print(f"✅ تم إنشاء قيد محاسبي للفاتورة {invoice.invoice_number}: {invoice.amount:,.2f} ريال")
    return journal_entry


def create_customer_payment_journal_entry(invoice, paid_amount, payment_method):
    """
    إنشاء قيد محاسبي لتسديد فاتورة عميل

    المدين: البنك/الصندوق (110001/110002)
    الدائن: العملاء (120001)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account
    from datetime import datetime
    from flask_login import current_user

    # حساب البنك أو الصندوق
    if payment_method == 'bank_transfer':
        bank_account = Account.query.filter_by(code='110002').first()
        if not bank_account:
            bank_account = Account(
                code='110002',
                name='Bank Account',
                name_ar='البنك',
                account_type='asset',
                nature='debit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(bank_account)
    else:
        bank_account = Account.query.filter_by(code='110001').first()
        if not bank_account:
            bank_account = Account(
                code='110001',
                name='Cash',
                name_ar='الصندوق',
                account_type='asset',
                nature='debit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(bank_account)

    # حساب العملاء
    customers = Account.query.filter_by(code='120001').first()
    if not customers:
        customers = Account(
            code='120001',
            name='Customers',
            name_ar='العملاء',
            account_type='asset',
            nature='debit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(customers)

    db.session.commit()

    # إنشاء رقم قيد فريد
    today = datetime.now().date()
    last_entry = JournalEntry.query.order_by(JournalEntry.entry_number.desc()).first()
    if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JE-'):
        try:
            last_num = int(last_entry.entry_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1

    entry_number = f"JE-{today.year}-{str(new_num).zfill(5)}"

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=today,
        description=f'تسديد فاتورة {invoice.invoice_number} - طريقة الدفع: {payment_method}',
        reference_type='customer_payment',
        reference_id=invoice.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد
    # مدين: البنك/الصندوق
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=bank_account.id,
        debit=paid_amount,
        credit=0,
        description=f'استلام مبلغ من العميل'
    )
    db.session.add(detail1)

    # دائن: العملاء
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=customers.id,
        debit=0,
        credit=paid_amount,
        description=f'تخفيض رصيد العميل'
    )
    db.session.add(detail2)

    db.session.commit()

    print(f"✅ تم إنشاء قيد محاسبي لتسديد {paid_amount:,.2f} ريال من الفاتورة {invoice.invoice_number}")
    return journal_entry


def create_company_payment_journal_entry(payment):
    """
    إنشاء قيد محاسبي لدفع مبلغ لشركة (مصروف)

    المدين: مصروف خدمات الشركات (520001)
    الدائن: البنك/الصندوق (110001/110002)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account
    from flask_login import current_user

    # حساب المصروفات
    expense_account = Account.query.filter_by(code='520001').first()
    if not expense_account:
        expense_account = Account(
            code='520001',
            name='Company Services Expense',
            name_ar='مصروف خدمات الشركات',
            account_type='expense',
            nature='debit',
            opening_balance=0,
            is_active=True
        )
        db.session.add(expense_account)

    # حساب البنك أو الصندوق
    if payment.payment_method == 'cash':
        bank_account = Account.query.filter_by(code='110001').first()
        if not bank_account:
            bank_account = Account(
                code='110001',
                name='Cash',
                name_ar='الصندوق',
                account_type='asset',
                nature='debit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(bank_account)
    else:
        bank_account = Account.query.filter_by(code='110002').first()
        if not bank_account:
            bank_account = Account(
                code='110002',
                name='Bank Account',
                name_ar='البنك',
                account_type='asset',
                nature='debit',
                opening_balance=0,
                is_active=True
            )
            db.session.add(bank_account)

    db.session.commit()

    # إنشاء رقم قيد فريد
    last_entry = JournalEntry.query.order_by(JournalEntry.entry_number.desc()).first()
    if last_entry and last_entry.entry_number and last_entry.entry_number.startswith('JE-'):
        try:
            last_num = int(last_entry.entry_number.split('-')[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1

    entry_number = f"JE-{payment.payment_date.year}-{str(new_num).zfill(5)}"

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=payment.payment_date,
        description=f'دفع مستحقات للشركة {payment.company.name} - {payment.reference_number or ""}',
        reference_type='company_payment',
        reference_id=payment.id,
        created_by=current_user.id if hasattr(current_user, 'id') else 1
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد
    # مدين: مصروف خدمات الشركات
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=expense_account.id,
        debit=payment.amount,
        credit=0,
        description=f'دفع لشركة {payment.company.name}'
    )
    db.session.add(detail1)

    # دائن: البنك/الصندوق
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=bank_account.id,
        debit=0,
        credit=payment.amount,
        description=f'تسديد مستحقات شركة {payment.company.name}'
    )
    db.session.add(detail2)

    db.session.commit()

    print(f"✅ تم إنشاء قيد محاسبي لدفع {payment.amount:,.2f} ريال للشركة {payment.company.name}")
    return journal_entry


# ==================== دوال مساعدة للتحقق من الحسابات ====================

def ensure_accounts_exist():
    """التأكد من وجود جميع الحسابات المحاسبية الأساسية"""
    from models import db, Account

    accounts = [
        # الأصول (1xxxxx)
        ('110001', 'Cash', 'الصندوق', 'asset', 'debit'),
        ('110002', 'Bank Account', 'البنك', 'asset', 'debit'),
        ('120001', 'Customers', 'العملاء', 'asset', 'debit'),
        ('130001', 'Advances', 'السلف', 'asset', 'debit'),

        # الخصوم (2xxxxx)
        ('210001', 'Salaries Payable', 'الرواتب المستحقة', 'liability', 'credit'),
        ('210002', 'Overtime Payable', 'مستحقات الإضافي', 'liability', 'credit'),
        ('220001', 'Suppliers', 'الدائنون - موردين', 'liability', 'credit'),
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
        ('520001', 'Company Services Expense', 'مصروف خدمات الشركات', 'expense', 'debit'),
        ('530001', 'Utilities Expense', 'كهرباء وماء', 'expense', 'debit'),
        ('530002', 'Rent Expense', 'إيجار', 'expense', 'debit'),
        ('530003', 'Office Supplies', 'مستلزمات مكتبية', 'expense', 'debit'),
        ('530004', 'Equipment Expense', 'معدات وأدوات', 'expense', 'debit'),
        ('530005', 'General Expense', 'مصروفات عامة', 'expense', 'debit'),
    ]

    created_count = 0
    for code, name, name_ar, account_type, nature in accounts:
        existing = Account.query.filter_by(code=code).first()
        if not existing:
            account = Account(
                code=code,
                name=name,
                name_ar=name_ar,
                account_type=account_type,
                nature=nature,
                opening_balance=0,
                is_active=True
            )
            db.session.add(account)
            created_count += 1

    if created_count > 0:
        db.session.commit()
        print(f"✅ تم إنشاء {created_count} حساب محاسبي جديد")
    else:
        print("✅ جميع الحسابات المحاسبية موجودة مسبقاً")

    return created_count



def get_next_entry_number():
    """الحصول على رقم القيد التالي بشكل صحيح"""
    from models import JournalEntry
    from datetime import datetime

    current_year = datetime.now().year

    # البحث عن أكبر رقم قيد في السنة الحالية
    pattern = f'JE-{current_year}-%'
    last_entry = JournalEntry.query.filter(
        JournalEntry.entry_number.like(pattern)
    ).order_by(JournalEntry.entry_number.desc()).first()

    if last_entry:
        # استخراج الرقم من JE-2026-00001
        try:
            parts = last_entry.entry_number.split('-')
            if len(parts) == 3:
                last_num = int(parts[2])
                new_num = last_num + 1
            else:
                new_num = 1
        except (IndexError, ValueError):
            new_num = 1
    else:
        new_num = 1

    # تنسيق الرقم بخمسة أرقام
    return f"JE-{current_year}-{str(new_num).zfill(5)}"