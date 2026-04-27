# utils.py
from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user
from datetime import datetime, timedelta
from models import db

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
    مع دعم الإجازات السنوية (مدفوعة وبدون أجر)
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
        'attendance_days': 0,          # أيام الحضور الفعلية (تحسب في الراتب)
        'absent_days': 0,              # أيام الغياب (تحسب كخصم)
        'sick_days': 0,                # أيام الإجازة المرضية
        'late_minutes_total': 0,       # إجمالي دقائق التأخير
        'paid_leave_days': 0,          # أيام الإجازة السنوية المدفوعة (تحسب في الراتب)
        'unpaid_leave_days': 0,        # أيام الإجازة السنوية بدون أجر
        'friday_attendance_days': 0,   # أيام الجمعة التي تم الحضور فيها
        'total_days': (end_date - start_date).days + 1,
        'work_days': 0,
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

            elif att.attendance_status == 'annual_leave':
                # إجازة سنوية مدفوعة الأجر
                days = att.annual_leave_days or 1
                summary['paid_leave_days'] += days
                if is_friday:
                    summary['friday_attendance_days'] += 1

            elif att.attendance_status == 'annual_leave_unpaid':
                # إجازة سنوية بدون أجر
                days = att.annual_leave_days or 1
                summary['unpaid_leave_days'] += days

            elif att.attendance_status == 'absent':
                if not is_friday:
                    summary['absent_days'] += 1
                else:
                    summary['friday_attendance_days'] += 1

            elif att.attendance_status == 'late':
                summary['attendance_days'] += 1
                summary['late_minutes_total'] += att.late_minutes or 0
                if is_friday:
                    summary['friday_attendance_days'] += 1
        else:
            # لا يوجد تسجيل لهذا اليوم
            if is_friday:
                pass
            else:
                summary['absent_days'] += 1

        current_date += timedelta(days=1)

    # حساب أيام العمل الفعلية
    friday_count = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 4:
            friday_count += 1
        current_date += timedelta(days=1)

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
    from models import db, JournalEntry, JournalEntryDetail, Account  # ✅ أضف db
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
    from models import db, JournalEntry, JournalEntryDetail, SupplierInvoice  # ✅ أضف db

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
    from models import db, JournalEntry, JournalEntryDetail, Account
    from utils import get_next_entry_number

    # ✅ تعريف الحسابات داخل الدالة
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

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=get_next_entry_number(),
        date=salary.created_at.date() if salary.created_at else datetime.now().date(),
        description=f'استحقاق راتب {salary.employee.name} عن {salary.notes or salary.month_year}',
        reference_type='salary_accrual',
        reference_id=salary.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: مصروف الرواتب
    detail1 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=salary_expense.id,
        debit=salary.total_salary,
        credit=0,
        description=f'راتب {salary.employee.name}'
    )
    db.session.add(detail1)

    # دائن: الرواتب المستحقة
    detail2 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=salaries_payable.id,
        debit=0,
        credit=salary.total_salary,
        description=f'استحقاق راتب {salary.employee.name}'
    )
    db.session.add(detail2)

    db.session.commit()
    return journal_entry


def create_salary_journal_entry(salary):
    """
    إنشاء قيد محاسبي مفصل للراتب
    يقوم بتوزيع المصروفات على الحسابات التفصيلية:
    - مصروف رواتب العمال الأساسية (511001)
    - مصروف بدل سكن العمال (511002)
    - مصروف بدل ملابس العمال (511004)
    - مصروف بطائق صحية للعمال (511005)
    - مصروف تأمين العمال (511003)
    """
    from models import db, JournalEntry, JournalEntryDetail, Account, Employee
    from datetime import datetime
    from utils import get_next_entry_number

    employee = Employee.query.get(salary.employee_id)

    # ========== 1. التأكد من وجود الحسابات ==========

    # حسابات المصروفات التفصيلية
    basic_expense = Account.query.filter_by(code='511001').first()
    if not basic_expense:
        basic_expense = Account(
            code='511001', name='Labor Basic Salary', name_ar='مصروف رواتب العمال الأساسية',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(basic_expense)

    resident_expense = Account.query.filter_by(code='511002').first()
    if not resident_expense:
        resident_expense = Account(
            code='511002', name='Labor Resident Allowance', name_ar='مصروف بدل سكن العمال',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(resident_expense)

    insurance_expense = Account.query.filter_by(code='511003').first()
    if not insurance_expense:
        insurance_expense = Account(
            code='511003', name='Labor Insurance', name_ar='مصروف تأمين العمال',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(insurance_expense)

    clothing_expense = Account.query.filter_by(code='511004').first()
    if not clothing_expense:
        clothing_expense = Account(
            code='511004', name='Labor Clothing Allowance', name_ar='مصروف بدل ملابس العمال',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(clothing_expense)

    health_expense = Account.query.filter_by(code='511005').first()
    if not health_expense:
        health_expense = Account(
            code='511005', name='Labor Health Cards', name_ar='مصروف بطائق صحية للعمال',
            account_type='expense', nature='debit', opening_balance=0, is_active=True
        )
        db.session.add(health_expense)

    # حسابات المستحقات
    salaries_payable = Account.query.filter_by(code='210001').first()
    if not salaries_payable:
        salaries_payable = Account(
            code='210001', name='Salaries Payable', name_ar='الرواتب المستحقة',
            account_type='liability', nature='credit', opening_balance=0, is_active=True
        )
        db.session.add(salaries_payable)

    allowances_payable = Account.query.filter_by(code='211002').first()
    if not allowances_payable:
        allowances_payable = Account(
            code='211002', name='Allowances Payable', name_ar='بدلات العمال المستحقة',
            account_type='liability', nature='credit', opening_balance=0, is_active=True
        )
        db.session.add(allowances_payable)

    insurance_payable = Account.query.filter_by(code='211003').first()
    if not insurance_payable:
        insurance_payable = Account(
            code='211003', name='Insurance Payable', name_ar='تأمينات مستحقة',
            account_type='liability', nature='credit', opening_balance=0, is_active=True
        )
        db.session.add(insurance_payable)

    db.session.commit()

    # ========== 2. المبالغ المراد ترحيلها ==========

    if employee and employee.employee_type == 'worker':
        basic_amount = salary.basic_salary_amount or 0
        resident_amount = salary.resident_allowance_amount or 0
        clothing_amount = salary.clothing_allowance_amount or 0
        health_amount = salary.health_card_amount or 0
        insurance_amount = salary.insurance_amount or 0
        cash_amount = salary.total_salary or 0
    else:
        # للمشرفين والإداريين
        basic_amount = salary.total_salary or 0
        resident_amount = 0
        clothing_amount = 0
        health_amount = 0
        insurance_amount = 0
        cash_amount = salary.total_salary or 0

    # ========== 3. إنشاء القيد المحاسبي ==========

    entry_number = get_next_entry_number()

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'استحقاق راتب {salary.employee.name} عن {salary.notes or salary.month_year}',
        reference_type='salary',
        reference_id=salary.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # ========== 4. المدين: المصروفات ==========

    if basic_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=basic_expense.id,
            debit=basic_amount,
            credit=0,
            description=f'الراتب الأساسي - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ مدين: مصروف رواتب العمال الأساسية: {basic_amount:,.0f} ريال')

    if resident_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=resident_expense.id,
            debit=resident_amount,
            credit=0,
            description=f'بدل سكن - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ مدين: مصروف بدل سكن العمال: {resident_amount:,.0f} ريال')

    if clothing_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=clothing_expense.id,
            debit=clothing_amount,
            credit=0,
            description=f'بدل ملابس - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ مدين: مصروف بدل ملابس العمال: {clothing_amount:,.0f} ريال')

    if health_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=health_expense.id,
            debit=health_amount,
            credit=0,
            description=f'بطاقة صحية - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ مدين: مصروف بطائق صحية للعمال: {health_amount:,.0f} ريال')

    if insurance_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=insurance_expense.id,
            debit=insurance_amount,
            credit=0,
            description=f'تأمين - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ مدين: مصروف تأمين العمال: {insurance_amount:,.0f} ريال')

    # ========== 5. الدائن: المستحقات ==========

    if cash_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=salaries_payable.id,
            debit=0,
            credit=cash_amount,
            description=f'راتب نقدي مستحق - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ دائن: الرواتب المستحقة: {cash_amount:,.0f} ريال')

    total_allowances = clothing_amount + health_amount
    if total_allowances > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=allowances_payable.id,
            debit=0,
            credit=total_allowances,
            description=f'بدلات مستحقة - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ دائن: بدلات العمال المستحقة: {total_allowances:,.0f} ريال')

    if insurance_amount > 0:
        detail = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=insurance_payable.id,
            debit=0,
            credit=insurance_amount,
            description=f'تأمينات مستحقة - {salary.employee.name}'
        )
        db.session.add(detail)
        print(f'   ✅ دائن: تأمينات مستحقة: {insurance_amount:,.0f} ريال')

    db.session.commit()

    salary.journal_entry_id = journal_entry.id
    db.session.commit()

    print(f'\n✅ تم إنشاء القيد المحاسبي: {entry_number}')
    print(
        f'   إجمالي المدين: {basic_amount + resident_amount + clothing_amount + health_amount + insurance_amount:,.0f} ريال')
    print(f'   إجمالي الدائن: {cash_amount + total_allowances + insurance_amount:,.0f} ريال')

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
    """إنشاء قيد محاسبي للفاتورة (عملاء)"""
    from models import Account, db
    from utils import create_journal_entry

    # الحصول على حسابات العملاء والإيرادات
    receivable_account = Account.query.filter_by(code='120001').first()
    revenue_account = Account.query.filter_by(code='410003').first()  # إيرادات الفواتير الإضافية

    if not receivable_account:
        raise ValueError("حساب العملاء (120001) غير موجود")

    if not revenue_account:
        raise ValueError("حساب إيرادات الفواتير الإضافية (410003) غير موجود")

    entries = [
        (receivable_account.id, invoice.amount, 0, f'فاتورة رقم {invoice.invoice_number}'),
        (revenue_account.id, 0, invoice.amount, f'إيرادات فاتورة {invoice.invoice_number}')
    ]

    return create_journal_entry(
        date=invoice.invoice_date,
        description=f'فاتورة رقم {invoice.invoice_number} - {invoice.contract.company.name if invoice.contract else "عميل"}',
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
    from utils import get_next_entry_number  # ✅ أضف هذا السطر


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
    from datetime import datetime
    from utils import get_next_entry_number, create_journal_entry

    # حساب المصروفات حسب الفئة
    expense_accounts = {
        'utilities': '530001',  # كهرباء وماء
        'rent': '530002',  # إيجار
        'office': '530003',  # مستلزمات مكتبية
        'equipment': '530004',  # معدات وأدوات
        'general': '590001'  # مصروفات عامة
    }

    # تحديد الحساب بناءً على فئة المصروف
    category_name = invoice.category.name if invoice.category else 'general'
    account_code = expense_accounts.get(category_name, '590001')

    expense_account = Account.query.filter_by(code=account_code).first()
    payable_account = Account.query.filter_by(code='220001').first()

    if not expense_account:
        raise ValueError(f"حساب المصروف غير موجود للكود: {account_code}")

    if not payable_account:
        raise ValueError("حساب الدائنون (220001) غير موجود")

    # إنشاء قيد محاسبي
    entries = [
        (expense_account.id, invoice.amount, 0, f'فاتورة {invoice.invoice_number}'),
        (payable_account.id, 0, invoice.amount, f'استحقاق فاتورة {invoice.invoice_number}')
    ]

    return create_journal_entry(
        date=invoice.invoice_date,
        description=f'فاتورة واردة من {invoice.supplier.name_ar} - {invoice.category.name_ar if invoice.category else "مصروفات"}',
        entries=entries,
        reference_type='supplier_invoice',
        reference_id=invoice.id
    )

def create_supplier_invoice_payment_journal_entry(invoice, payment_amount, payment_method):
    """إنشاء قيد محاسبي لتسديد فاتورة مورد"""
    from models import Account, JournalEntry, JournalEntryDetail, db
    from flask_login import current_user
    from utils import get_next_entry_number  # ✅ أضف هذا السطر


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
    from utils import get_next_entry_number  # ✅ أضف هذا السطر


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
    """الحصول على رقم القيد التالي بشكل فريد وآمن"""
    from models import JournalEntry
    from datetime import datetime
    from sqlalchemy import func

    current_year = datetime.now().year

    # ✅ 1. البحث عن أكبر رقم تسلسلي موجود فعليًا
    result = db.session.query(
        func.max(JournalEntry.entry_number)
    ).filter(
        JournalEntry.entry_number.like(f'JE-{current_year}-%')
    ).scalar()

    if result:
        try:
            # استخراج الجزء الرقمي من JE-2026-00001
            last_num = int(result.split('-')[2])
            new_num = last_num + 1
        except (IndexError, ValueError):
            new_num = 1
    else:
        new_num = 1

    # ✅ 2. حلقة أمان للتأكد من أن الرقم الجديد غير موجود مسبقًا
    while True:
        candidate_number = f"JE-{current_year}-{str(new_num).zfill(5)}"
        if not JournalEntry.query.filter_by(entry_number=candidate_number).first():
            return candidate_number
        new_num += 1  # جرب الرقم التالي إذا كان موجودًا

def create_management_salary_transfer():
    """
    إنشاء ترحيل مخصص للمدير والمشرف (رواتب ثابتة بدون حساب حضور)
    """
    from models import db, Employee, AttendancePeriodTransfer, AttendancePeriodTransferDetail
    from datetime import datetime, timedelta

    # البحث عن المدير والمشرف
    admin = Employee.query.filter_by(employee_type='admin', is_active=True).first()
    supervisor = Employee.query.filter_by(employee_type='supervisor', is_active=True).first()

    if not admin and not supervisor:
        return {'success': False, 'message': 'لا يوجد مدير أو مشرف في النظام'}

    # تاريخ الفترة (الشهر الحالي)
    today = datetime.now().date()
    start_date = today.replace(day=1)
    if today.month == 12:
        end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    period_name = f'رواتب الإدارة - {today.strftime("%B %Y")}'

    # التحقق من عدم وجود ترحيل سابق
    existing = AttendancePeriodTransfer.query.filter_by(period_name=period_name).first()
    if existing:
        return {'success': False, 'message': f'يوجد ترحيل مسبق: {period_name}'}

    # إنشاء ترحيل جديد
    transfer = AttendancePeriodTransfer(
        period_name=period_name,
        start_date=start_date,
        end_date=end_date,
        transfer_date=today,
        transferred_by=1,
        is_transferred=False,
        notes='ترحيل مخصص للمدير والمشرف (رواتب ثابتة)'
    )
    db.session.add(transfer)
    db.session.flush()

    employees_added = []

    # إضافة المدير
    if admin:
        # عدد أيام الشهر كاملاً
        days_in_month = (end_date - start_date).days + 1

        detail = AttendancePeriodTransferDetail(
            transfer_id=transfer.id,
            employee_id=admin.id,
            attendance_days=days_in_month,  # كل أيام الشهر
            absent_days=0,
            sick_days=0,
            late_minutes_total=0,
            overtime_hours=0,
            is_processed=False
        )
        db.session.add(detail)
        employees_added.append({'name': admin.name, 'type': 'مدير', 'salary': admin.salary})

    # إضافة المشرف
    if supervisor:
        days_in_month = (end_date - start_date).days + 1

        detail = AttendancePeriodTransferDetail(
            transfer_id=transfer.id,
            employee_id=supervisor.id,
            attendance_days=days_in_month,
            absent_days=0,
            sick_days=0,
            late_minutes_total=0,
            overtime_hours=0,
            is_processed=False
        )
        db.session.add(detail)
        employees_added.append({'name': supervisor.name, 'type': 'مشرف', 'salary': supervisor.salary})

    db.session.commit()

    return {
        'success': True,
        'message': f'تم إنشاء ترحيل للإدارة',
        'transfer_id': transfer.id,
        'period_name': period_name,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'employees': employees_added
    }

# أضف هذه الدالة في ملف utils.py أو في مكان مناسب

def check_existing_transfer(payroll_type, company_id=None, region=None, start_date=None, end_date=None):
    """
    التحقق من وجود ترحيل مسبق لنفس الفترة والنوع

    Args:
        payroll_type: نوع الراتب ('admin' أو 'labor')
        company_id: معرف الشركة (اختياري)
        region: المنطقة (اختياري)
        start_date: تاريخ البداية
        end_date: تاريخ النهاية

    Returns:
        AttendancePeriodTransfer or None: الترحيل الموجود أو None
    """
    from models import AttendancePeriodTransfer

    query = AttendancePeriodTransfer.query.filter(
        AttendancePeriodTransfer.payroll_type == payroll_type
    )

    if start_date and end_date:
        query = query.filter(
            AttendancePeriodTransfer.start_date <= end_date,
            AttendancePeriodTransfer.end_date >= start_date
        )

    if company_id:
        query = query.filter(AttendancePeriodTransfer.company_id == company_id)
    elif region:
        query = query.filter(AttendancePeriodTransfer.region == region)

    return query.first()

# أضف هذه الدوال في نهاية ملف utils.py

# ==================== دوال ترحيل الرواتب المفصولة ====================

def transfer_admin_payroll(company_id, period_name, start_date, end_date, created_by=1):
    """
    ترحيل رواتب الإدارة فقط (شركة واحدة)

    Args:
        company_id: معرف الشركة
        period_name: اسم الفترة (مثال: رواتب إبريل 2026)
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        created_by: معرف المستخدم المنشئ

    Returns:
        dict: نتيجة العملية
    """
    from models import db, AttendancePeriodTransfer, AttendancePeriodTransferDetail, Employee

    # التحقق من وجود ترحيل مسبق لنفس الفترة والنوع
    existing = check_existing_transfer(
        payroll_type='admin',
        company_id=company_id,
        start_date=start_date,
        end_date=end_date
    )

    if existing:
        return {
            'success': False,
            'message': f'❌ يوجد ترحيل مسبق: {existing.period_name} - {existing.get_payroll_type_name()}',
            'existing_transfer': existing
        }

    # جلب موظفي الإدارة فقط (admin, supervisor)
    admin_employees = Employee.query.filter(
        Employee.is_active == True,
        Employee.company_id == company_id,
        Employee.employee_type.in_(['admin', 'supervisor'])
    ).all()

    if not admin_employees:
        return {
            'success': False,
            'message': '⚠️ لا يوجد موظفين إدارة في هذه الشركة',
            'employees_found': 0
        }

    # إنشاء ترحيل جديد
    transfer = AttendancePeriodTransfer(
        period_name=period_name,
        payroll_type='admin',
        start_date=start_date,
        end_date=end_date,
        transfer_date=datetime.now().date(),
        company_id=company_id,
        is_transferred=False,
        created_at=datetime.utcnow()
    )
    db.session.add(transfer)
    db.session.flush()

    # إضافة تفاصيل الترحيل لكل موظف
    details_added = []
    for employee in admin_employees:
        # حساب إحصائيات الحضور للموظف
        summary = get_employee_attendance_summary(employee, start_date, end_date)

        # الحصول على المعاملات المالية غير المسواة
        transactions = employee.get_unsettled_transactions_total()

        # حساب قيم الخصومات
        advance_amount = transactions.get('advance', 0)
        deduction_amount = transactions.get('deduction', 0)
        penalty_amount = transactions.get('penalty', 0)

        # حساب خصم الغياب (مع مراعاة أيام الغياب فقط)
        daily_rate = employee.salary / 30 if employee.salary else 0
        absence_deduction = daily_rate * summary['absent_days']

        # حساب مبلغ الحضور
        attendance_amount = daily_rate * summary['attendance_days']

        # حساب البدل اليومي (للساكنين)
        daily_allowance = get_employee_daily_allowance(employee, summary['attendance_days'])

        # حساب ساعات الإضافي والمبلغ
        overtime_hours = get_employee_overtime_hours(employee, start_date, end_date)
        hourly_rate = daily_rate / 8
        overtime_amount = overtime_hours * (hourly_rate * 1.5)

        # حساب الإجماليات
        total_additions = attendance_amount + daily_allowance + overtime_amount
        total_deductions = absence_deduction + advance_amount + deduction_amount + penalty_amount
        final_amount = total_additions - total_deductions

        detail = AttendancePeriodTransferDetail(
            transfer_id=transfer.id,
            employee_id=employee.id,
            attendance_days=summary['attendance_days'],
            absent_days=summary['absent_days'],
            sick_days=summary['sick_days'],
            late_minutes_total=summary['late_minutes_total'],
            overtime_hours=overtime_hours,
            daily_allowance=daily_allowance,
            base_salary=employee.salary or 0,
            attendance_amount=attendance_amount,
            overtime_amount=overtime_amount,
            daily_allowance_amount=daily_allowance,
            advance_amount=advance_amount,
            deduction_amount=deduction_amount,
            penalty_amount=penalty_amount,
            absence_deduction=absence_deduction,
            total_additions=total_additions,
            total_deductions=total_deductions,
            final_amount=final_amount,
            is_processed=False,
            notes=f'ترحيل آلي لرواتب الإدارة - {period_name}'
        )
        db.session.add(detail)
        details_added.append({
            'employee_name': employee.name,
            'attendance_days': summary['attendance_days'],
            'final_amount': final_amount
        })

    # تحديث إحصائيات الترحيل
    transfer.total_employees = len(details_added)
    transfer.total_attendance_days = sum(d.attendance_days for d in transfer.transfers_details)
    transfer.total_salaries = sum(d.base_salary for d in transfer.transfers_details)
    transfer.total_deductions = sum(d.total_deductions for d in transfer.transfers_details)
    transfer.total_net = sum(d.final_amount for d in transfer.transfers_details)

    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم ترحيل رواتب الإدارة بنجاح ({len(details_added)} موظف)',
        'transfer_id': transfer.id,
        'period_name': period_name,
        'total_employees': transfer.total_employees,
        'total_net': transfer.total_net,
        'details': details_added
    }


def transfer_labor_payroll(company_id, period_name, start_date, end_date, created_by=1):
    """
    ترحيل رواتب العمال فقط

    Args:
        company_id: معرف الشركة
        period_name: اسم الفترة (مثال: رواتب عمال إبريل 2026)
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        created_by: معرف المستخدم المنشئ

    Returns:
        dict: نتيجة العملية
    """
    from models import db, AttendancePeriodTransfer, AttendancePeriodTransferDetail, Employee

    # التحقق من وجود ترحيل مسبق لنفس الفترة والنوع
    existing = check_existing_transfer(
        payroll_type='labor',
        company_id=company_id,
        start_date=start_date,
        end_date=end_date
    )

    if existing:
        return {
            'success': False,
            'message': f'❌ يوجد ترحيل مسبق لرواتب العمال: {existing.period_name}',
            'existing_transfer': existing
        }

    # جلب موظفي العمال فقط
    labor_employees = Employee.query.filter(
        Employee.is_active == True,
        Employee.company_id == company_id,
        Employee.employee_type == 'worker'
    ).all()

    if not labor_employees:
        return {
            'success': False,
            'message': '⚠️ لا يوجد عمال في هذه الشركة',
            'employees_found': 0
        }

    # إنشاء ترحيل جديد
    transfer = AttendancePeriodTransfer(
        period_name=period_name,
        payroll_type='labor',
        start_date=start_date,
        end_date=end_date,
        transfer_date=datetime.now().date(),
        company_id=company_id,
        is_transferred=False,
        created_at=datetime.utcnow()
    )
    db.session.add(transfer)
    db.session.flush()

    # إضافة تفاصيل الترحيل لكل عامل
    details_added = []
    for employee in labor_employees:
        # حساب إحصائيات الحضور
        summary = get_employee_attendance_summary(employee, start_date, end_date)

        # الحصول على المعاملات المالية
        transactions = employee.get_unsettled_transactions_total()

        # حساب الراتب حسب نظام العمل
        work_type = getattr(employee, 'work_type', 'daily')
        daily_wage = getattr(employee, 'daily_wage', 50)
        hourly_rate = getattr(employee, 'hourly_rate', daily_wage / 8)

        if work_type == 'daily':
            attendance_amount = daily_wage * summary['attendance_days']
            base_salary = attendance_amount
        elif work_type == 'hourly':
            attendance_amount = hourly_rate * (summary['attendance_days'] * 8)
            base_salary = attendance_amount
        else:  # piece
            piece_rate = getattr(employee, 'piece_rate', 0)
            pieces_count = getattr(employee, 'pieces_count', 0)
            attendance_amount = piece_rate * pieces_count
            base_salary = attendance_amount

        # حساب الإضافي (1.5 × الأجر العادي للساعة)
        overtime_hours = get_employee_overtime_hours(employee, start_date, end_date)
        hourly_rate = daily_wage / 8
        overtime_amount = overtime_hours * (hourly_rate * 1.5)

        # خصم الغياب
        absence_deduction = daily_wage * summary['absent_days']

        # الإضافات والخصومات
        daily_allowance = get_employee_daily_allowance(employee, summary['attendance_days'])

        advance_amount = transactions.get('advance', 0)
        deduction_amount = transactions.get('deduction', 0)
        penalty_amount = transactions.get('penalty', 0)

        # الإجماليات
        total_additions = attendance_amount + overtime_amount + daily_allowance
        total_deductions = absence_deduction + advance_amount + deduction_amount + penalty_amount
        final_amount = total_additions - total_deductions

        detail = AttendancePeriodTransferDetail(
            transfer_id=transfer.id,
            employee_id=employee.id,
            attendance_days=summary['attendance_days'],
            absent_days=summary['absent_days'],
            sick_days=summary['sick_days'],
            late_minutes_total=summary['late_minutes_total'],
            overtime_hours=overtime_hours,
            daily_allowance=daily_allowance,
            base_salary=base_salary,
            attendance_amount=attendance_amount,
            overtime_amount=overtime_amount,
            daily_allowance_amount=daily_allowance,
            advance_amount=advance_amount,
            deduction_amount=deduction_amount,
            penalty_amount=penalty_amount,
            absence_deduction=absence_deduction,
            total_additions=total_additions,
            total_deductions=total_deductions,
            final_amount=final_amount,
            is_processed=False,
            notes=f'ترحيل آلي لرواتب العمال - {period_name}'
        )
        db.session.add(detail)
        details_added.append({
            'employee_name': employee.name,
            'work_type': work_type,
            'attendance_days': summary['attendance_days'],
            'final_amount': final_amount
        })

    # تحديث إحصائيات الترحيل
    transfer.total_employees = len(details_added)
    transfer.total_attendance_days = sum(d.attendance_days for d in transfer.transfers_details)
    transfer.total_salaries = sum(d.base_salary for d in transfer.transfers_details)
    transfer.total_deductions = sum(d.total_deductions for d in transfer.transfers_details)
    transfer.total_net = sum(d.final_amount for d in transfer.transfers_details)

    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم ترحيل رواتب العمال بنجاح ({len(details_added)} عامل)',
        'transfer_id': transfer.id,
        'period_name': period_name,
        'total_employees': transfer.total_employees,
        'total_net': transfer.total_net,
        'details': details_added
    }


def process_transfer_to_salaries(transfer_id):
    """
    معالجة الترحيل وإنشاء سجلات الرواتب

    Args:
        transfer_id: معرف الترحيل

    Returns:
        dict: نتيجة العملية
    """
    from models import db, AttendancePeriodTransfer, AttendancePeriodTransferDetail, Salary
    from datetime import datetime

    transfer = AttendancePeriodTransfer.query.get(transfer_id)

    if not transfer:
        return {'success': False, 'message': 'الترحيل غير موجود'}

    if transfer.is_transferred:
        return {'success': False, 'message': f'الترحيل {transfer.period_name} تمت معالجته مسبقاً'}

    # إنشاء سلسلة month_year
    month_year = f"{transfer.start_date.month:02d}-{transfer.start_date.year}"

    salaries_created = []

    for detail in transfer.transfers_details:
        employee = detail.employee

        # البحث عن راتب موجود
        salary = Salary.query.filter_by(
            employee_id=employee.id,
            month_year=month_year
        ).first()

        if not salary:
            salary = Salary(
                employee_id=employee.id,
                month_year=month_year,
                base_salary=detail.base_salary,
                notes=f'من ترحيل: {transfer.period_name}'
            )
            db.session.add(salary)

        # تحديث بيانات الراتب
        salary.attendance_days = detail.attendance_days
        salary.attendance_amount = detail.attendance_amount
        salary.daily_allowance_amount = detail.daily_allowance_amount
        salary.overtime_amount = detail.overtime_amount
        salary.advance_amount = detail.advance_amount
        salary.deduction_amount = detail.deduction_amount
        salary.penalty_amount = detail.penalty_amount
        salary.total_salary = detail.final_amount

        detail.is_processed = True
        detail.processed_at = datetime.now()
        detail.salary_id = salary.id

        salaries_created.append({
            'employee_id': employee.id,
            'employee_name': employee.name,
            'salary': detail.final_amount
        })

    # تحديث حالة الترحيل
    transfer.is_transferred = True
    transfer.transferred_by = 1  # يمكن تعديله حسب المستخدم الحالي
    transfer.transfer_date = datetime.now().date()

    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم معالجة {len(salaries_created)} راتب',
        'transfer_id': transfer.id,
        'salaries': salaries_created
    }


def get_transfers_by_type(payroll_type, company_id=None):
    """
    الحصول على قائمة الترحيلات حسب النوع

    Args:
        payroll_type: نوع الراتب ('admin' أو 'labor')
        company_id: معرف الشركة (اختياري)

    Returns:
        list: قائمة الترحيلات
    """
    from models import AttendancePeriodTransfer

    query = AttendancePeriodTransfer.query.filter_by(payroll_type=payroll_type)

    if company_id:
        query = query.filter_by(company_id=company_id)

    return query.order_by(AttendancePeriodTransfer.start_date.desc()).all()


def delete_transfer(transfer_id):
    """
    حذف ترحيل بالكامل

    Args:
        transfer_id: معرف الترحيل

    Returns:
        dict: نتيجة العملية
    """
    from models import db, AttendancePeriodTransfer, AttendancePeriodTransferDetail

    transfer = AttendancePeriodTransfer.query.get(transfer_id)

    if not transfer:
        return {'success': False, 'message': 'الترحيل غير موجود'}

    if transfer.is_transferred:
        return {'success': False, 'message': 'لا يمكن حذف ترحيل تمت معالجته بالفعل'}

    # حذف التفاصيل أولاً (سوف يتم تلقائياً بسبب cascade)
    db.session.delete(transfer)
    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم حذف الترحيل {transfer.period_name}',
        'transfer_id': transfer_id
    }


def get_transfer_summary(transfer_id):
    """
    الحصول على ملخص الترحيل مع التفاصيل

    Args:
        transfer_id: معرف الترحيل

    Returns:
        dict: ملخص الترحيل
    """
    from models import AttendancePeriodTransfer

    transfer = AttendancePeriodTransfer.query.get(transfer_id)

    if not transfer:
        return {'success': False, 'message': 'الترحيل غير موجود'}

    details = []
    for detail in transfer.transfers_details:
        details.append({
            'employee_id': detail.employee_id,
            'employee_name': detail.employee.name if detail.employee else None,
            'employee_code': detail.employee.code if detail.employee else None,
            'attendance_days': detail.attendance_days,
            'absent_days': detail.absent_days,
            'overtime_hours': detail.overtime_hours,
            'base_salary': detail.base_salary,
            'additions': detail.total_additions,
            'deductions': detail.total_deductions,
            'final_amount': detail.final_amount,
            'is_processed': detail.is_processed
        })

    return {
        'success': True,
        'transfer': {
            'id': transfer.id,
            'period_name': transfer.period_name,
            'payroll_type': transfer.payroll_type,
            'payroll_type_name': transfer.get_payroll_type_name(),
            'start_date': transfer.start_date.strftime('%Y-%m-%d'),
            'end_date': transfer.end_date.strftime('%Y-%m-%d'),
            'company_name': transfer.company.name if transfer.company else None,
            'total_employees': transfer.total_employees,
            'total_attendance_days': transfer.total_attendance_days,
            'total_salaries': transfer.total_salaries,
            'total_deductions': transfer.total_deductions,
            'total_net': transfer.total_net,
            'is_transferred': transfer.is_transferred,
            'transfer_date': transfer.transfer_date.strftime('%Y-%m-%d') if transfer.transfer_date else None,
            'created_at': transfer.created_at.strftime('%Y-%m-%d %H:%M') if transfer.created_at else None
        },
        'details': details
    }


# ==================== دوال إدارة الترحيلات في القوالب ====================

def can_create_transfer(payroll_type, company_id, start_date, end_date):
    """
    التحقق من إمكانية إنشاء ترحيل جديد

    Returns:
        tuple: (can_create, existing_transfer, message)
    """
    existing = check_existing_transfer(payroll_type, company_id, None, start_date, end_date)

    if existing:
        return False, existing, f'يوجد ترحيل مسبق: {existing.period_name}'

    return True, None, None


def get_employees_by_type(company_id, employee_type):
    """
    الحصول على الموظفين حسب النوع

    Args:
        company_id: معرف الشركة
        employee_type: 'admin', 'supervisor', 'worker'

    Returns:
        list: قائمة الموظفين
    """
    from models import Employee

    return Employee.query.filter(
        Employee.is_active == True,
        Employee.company_id == company_id,
        Employee.employee_type == employee_type
    ).all()


def get_admin_employees_count(company_id):
    """الحصول على عدد موظفي الإدارة في الشركة"""
    from models import Employee

    return Employee.query.filter(
        Employee.is_active == True,
        Employee.company_id == company_id,
        Employee.employee_type.in_(['admin', 'supervisor'])
    ).count()


def get_labor_employees_count(company_id):
    """الحصول على عدد العمال في الشركة"""
    from models import Employee

    return Employee.query.filter(
        Employee.is_active == True,
        Employee.company_id == company_id,
        Employee.employee_type == 'worker'
    ).count()

# أضف هذه الدوال إلى utils.py

def calculate_labor_monthly_cost(employee, attendance_days, month_year):
    """
    حساب التكلفة الشهرية الكاملة للعامل

    التوزيع:
    - الراتب الأساسي: 2000 شهرياً (موزع حسب أيام العمل)
    - بدل سكن: 500 لكل يوم عمل (للساكنين فقط)
    - التأمين: 10800 شهرياً لكل عامل
    - بدل ملابس: 24480 سنوياً (2040 شهرياً)
    - بطائق صحية: 15000 سنوياً (1250 شهرياً)

    Returns:
        dict: تفاصيل التكلفة
    """
    # الراتب الأساسي حسب أيام العمل
    daily_rate = employee.basic_salary / 30
    basic_salary = daily_rate * attendance_days

    # بدل السكن (للساكنين فقط)
    resident_allowance = 0
    if employee.is_resident:
        resident_allowance = 500 * attendance_days

    # التأمين الشهري (ثابت)
    insurance = employee.monthly_insurance  # 10800

    # بدل الملابس الشهري (تقسيط سنوي)
    monthly_clothing = employee.clothing_allowance / 12  # 24480 / 12 = 2040

    # بدل البطائق الصحية الشهري (تقسيط سنوي)
    monthly_health = employee.health_card_allowance / 12  # 15000 / 12 = 1250

    # إجمالي التكلفة الشهرية
    total_cost = basic_salary + resident_allowance + insurance + monthly_clothing + monthly_health

    return {
        'employee_id': employee.id,
        'employee_name': employee.name,
        'month_year': month_year,
        'attendance_days': attendance_days,
        'basic_salary': basic_salary,
        'resident_allowance': resident_allowance,
        'insurance': insurance,
        'clothing_allowance': monthly_clothing,
        'health_card_allowance': monthly_health,
        'total_cost': total_cost,
        'breakdown': {
            'basic_salary_formula': f'{employee.basic_salary} / 30 * {attendance_days} = {basic_salary:.2f}',
            'resident_formula': f'500 * {attendance_days} = {resident_allowance:.2f}' if employee.is_resident else 'غير ساكن',
            'insurance_formula': f'10800 شهرياً = {insurance:.2f}',
            'clothing_formula': f'24480 / 12 = {monthly_clothing:.2f}',
            'health_formula': f'15000 / 12 = {monthly_health:.2f}'
        }
    }


def calculate_all_labor_costs(company_id, attendance_data):
    """
    حساب تكاليف جميع العمال في الشركة

    Args:
        company_id: معرف الشركة
        attendance_data: dict {employee_id: attendance_days}

    Returns:
        dict: إجمالي التكاليف
    """
    from models import Employee, LaborMonthlyCost, db
    from datetime import datetime

    employees = Employee.query.filter_by(
        company_id=company_id,
        employee_type='worker',
        is_active=True
    ).all()

    month_year = datetime.now().strftime('%m-%Y')
    results = []
    total_basic = 0
    total_resident = 0
    total_insurance = 0
    total_clothing = 0
    total_health = 0
    total_all = 0

    for employee in employees:
        attendance_days = attendance_data.get(employee.id, 0)

        # حساب التكلفة
        cost = calculate_labor_monthly_cost(employee, attendance_days, month_year)

        # البحث عن سجل تكلفة موجود
        existing = LaborMonthlyCost.query.filter_by(
            employee_id=employee.id,
            month_year=month_year
        ).first()

        if existing:
            # تحديث السجل الموجود
            existing.basic_salary_cost = cost['basic_salary']
            existing.resident_allowance_cost = cost['resident_allowance']
            existing.insurance_cost = cost['insurance']
            existing.clothing_allowance_cost = cost['clothing_allowance']
            existing.health_card_cost = cost['health_card_allowance']
            existing.total_cost = cost['total_cost']
            existing.updated_at = datetime.utcnow()
        else:
            # إنشاء سجل جديد
            new_cost = LaborMonthlyCost(
                employee_id=employee.id,
                month_year=month_year,
                basic_salary_cost=cost['basic_salary'],
                resident_allowance_cost=cost['resident_allowance'],
                insurance_cost=cost['insurance'],
                clothing_allowance_cost=cost['clothing_allowance'],
                health_card_cost=cost['health_card_allowance'],
                total_cost=cost['total_cost']
            )
            db.session.add(new_cost)

        results.append(cost)

        # تجميع الإجماليات
        total_basic += cost['basic_salary']
        total_resident += cost['resident_allowance']
        total_insurance += cost['insurance']
        total_clothing += cost['clothing_allowance']
        total_health += cost['health_card_allowance']
        total_all += cost['total_cost']

    db.session.commit()

    return {
        'success': True,
        'month_year': month_year,
        'employees_count': len(results),
        'summary': {
            'total_basic_salaries': total_basic,
            'total_resident_allowances': total_resident,
            'total_insurance': total_insurance,
            'total_clothing_allowance': total_clothing,
            'total_health_cards': total_health,
            'grand_total': total_all
        },
        'details': results
    }


def create_labor_salary_journal_entry(salary_calculation):
    """
    إنشاء قيد محاسبي لرواتب العمال

    القيد يتكون من:
    مدين:
        - مصروف رواتب العمال الأساسية (511001)
        - مصروف بدل سكن العمال (511002)
        - مصروف تأمين العمال (511003)
        - مصروف بدل ملابس العمال (511004)
        - مصروف بطائق صحية للعمال (511005)

    دائن:
        - رواتب العمال المستحقة (211001)
        - بدلات العمال المستحقة (211002)
        - تأمينات مستحقة (211003)
    """
    from models import Account, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from utils import get_next_entry_number

    summary = salary_calculation['summary']

    # البحث عن الحسابات
    basic_salary_expense = Account.query.filter_by(code='511001').first()
    resident_allowance_expense = Account.query.filter_by(code='511002').first()
    insurance_expense = Account.query.filter_by(code='511003').first()
    clothing_expense = Account.query.filter_by(code='511004').first()
    health_expense = Account.query.filter_by(code='511005').first()

    salaries_payable = Account.query.filter_by(code='211001').first()
    allowances_payable = Account.query.filter_by(code='211002').first()
    insurance_payable = Account.query.filter_by(code='211003').first()

    # التأكد من وجود الحسابات
    if not all([basic_salary_expense, resident_allowance_expense, insurance_expense,
                clothing_expense, health_expense, salaries_payable, allowances_payable, insurance_payable]):
        # إنشاء الحسابات إذا لم تكن موجودة
        create_labor_accounts()
        # إعادة المحاولة
        basic_salary_expense = Account.query.filter_by(code='511001').first()
        resident_allowance_expense = Account.query.filter_by(code='511002').first()
        insurance_expense = Account.query.filter_by(code='511003').first()
        clothing_expense = Account.query.filter_by(code='511004').first()
        health_expense = Account.query.filter_by(code='511005').first()
        salaries_payable = Account.query.filter_by(code='211001').first()
        allowances_payable = Account.query.filter_by(code='211002').first()
        insurance_payable = Account.query.filter_by(code='211003').first()

    month_year = salary_calculation['month_year']
    entry_number = get_next_entry_number()

    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'رواتب وتكاليف العمال عن {month_year}',
        reference_type='labor_salaries',
        reference_id=None
    )
    db.session.add(journal_entry)
    db.session.flush()

    # إضافة تفاصيل القيد (مدين)
    details = [
        (basic_salary_expense.id, summary['total_basic_salaries'], 0, 'رواتب العمال الأساسية'),
        (resident_allowance_expense.id, summary['total_resident_allowances'], 0, 'بدل سكن العمال'),
        (insurance_expense.id, summary['total_insurance'], 0, 'تأمين العمال'),
        (clothing_expense.id, summary['total_clothing_allowance'], 0, 'بدل ملابس العمال'),
        (health_expense.id, summary['total_health_cards'], 0, 'بطائق صحية للعمال')
    ]

    for acc_id, amount, credit, desc in details:
        if amount > 0:
            detail = JournalEntryDetail(
                entry_id=journal_entry.id,
                account_id=acc_id,
                debit=amount,
                credit=credit,
                description=desc
            )
            db.session.add(detail)

    # إضافة تفاصيل القيد (دائن)
    # رواتب مستحقة (الراتب الأساسي + بدل السكن)
    total_salaries = summary['total_basic_salaries'] + summary['total_resident_allowances']

    credit_details = [
        (salaries_payable.id, total_salaries, 'رواتب العمال المستحقة'),
        (allowances_payable.id, summary['total_clothing_allowance'] + summary['total_health_cards'], 'بدلات العمال المستحقة'),
        (insurance_payable.id, summary['total_insurance'], 'تأمينات مستحقة')
    ]

    for acc_id, amount, desc in credit_details:
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


def create_contractor_annual_journal_entry(year, company_id):
    """
    إنشاء قيد محاسبي للمتعهد (ضريبة وزكاة سنوية)

    مدين:
        - مصروف ضريبة المتعهدين (521001)
        - مصروف زكاة المتعهدين (521002)

    دائن:
        - ضريبة مستحقة للجهات الضريبية (221001)
        - زكاة مستحقة (221002)
    """
    from models import Account, ContractorAnnualCost, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from utils import get_next_entry_number

    # البحث عن سجل التكلفة السنوية
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

    # البحث عن الحسابات
    tax_expense = Account.query.filter_by(code='521001').first()
    zakat_expense = Account.query.filter_by(code='521002').first()
    tax_payable = Account.query.filter_by(code='221001').first()
    zakat_payable = Account.query.filter_by(code='221002').first()

    if not all([tax_expense, zakat_expense, tax_payable, zakat_payable]):
        create_labor_accounts()
        tax_expense = Account.query.filter_by(code='521001').first()
        zakat_expense = Account.query.filter_by(code='521002').first()
        tax_payable = Account.query.filter_by(code='221001').first()
        zakat_payable = Account.query.filter_by(code='221002').first()

    entry_number = get_next_entry_number()

    # إنشاء القيد المحاسبي (إذا لم يتم ترحيله مسبقاً)
    if annual_cost.is_paid:
        return {'success': False, 'message': f'تم ترحيل تكاليف سنة {year} مسبقاً'}

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'إقفال ضريبة وزكاة المتعهد عن سنة {year}',
        reference_type='contractor_annual',
        reference_id=annual_cost.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: مصروفات الضريبة والزكاة
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

    # دائن: التزامات تجاه الجهات
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

    # تحديث حالة الترحيل
    annual_cost.is_paid = True
    annual_cost.paid_date = datetime.now().date()
    annual_cost.payment_reference = entry_number

    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم ترحيل ضريبة وزكاة سنة {year}',
        'entry_number': entry_number,
        'journal_entry': journal_entry
    }

def create_contractor_liability_journal_entry(year, company_id):
    """
    إنشاء قيد محاسبي لإظهار التزامات المتعهد تجاه الضريبة والزكاة

    عندما يدفع المتعهد:
    مدين: ضريبة مستحقة / زكاة مستحقة
    دائن: البنك / الصندوق
    """
    from models import Account, ContractorAnnualCost, JournalEntry, JournalEntryDetail, db
    from datetime import datetime
    from utils import get_next_entry_number

    annual_cost = ContractorAnnualCost.query.filter_by(
        year=year,
        company_id=company_id
    ).first()

    if not annual_cost:
        return {'success': False, 'message': f'لا توجد تكاليف مسجلة لسنة {year}'}

    # البحث عن الحسابات
    tax_payable = Account.query.filter_by(code='221001').first()
    zakat_payable = Account.query.filter_by(code='221002').first()
    bank_account = Account.query.filter_by(code='110002').first()  # البنك

    if not all([tax_payable, zakat_payable, bank_account]):
        return {'success': False, 'message': 'الحسابات المحاسبية غير مهيأة بشكل صحيح'}

    entry_number = get_next_entry_number()
    total_amount = annual_cost.tax_amount + annual_cost.zakat_amount

    journal_entry = JournalEntry(
        entry_number=entry_number,
        date=datetime.now().date(),
        description=f'سداد ضريبة وزكاة المتعهد عن سنة {year}',
        reference_type='contractor_payment',
        reference_id=annual_cost.id
    )
    db.session.add(journal_entry)
    db.session.flush()

    # مدين: تخفيض الالتزامات
    if annual_cost.tax_amount > 0:
        detail1 = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=tax_payable.id,
            debit=annual_cost.tax_amount,
            credit=0,
            description=f'سداد ضريبة سنة {year}'
        )
        db.session.add(detail1)

    if annual_cost.zakat_amount > 0:
        detail2 = JournalEntryDetail(
            entry_id=journal_entry.id,
            account_id=zakat_payable.id,
            debit=annual_cost.zakat_amount,
            credit=0,
            description=f'سداد زكاة سنة {year}'
        )
        db.session.add(detail2)

    # دائن: البنك
    detail3 = JournalEntryDetail(
        entry_id=journal_entry.id,
        account_id=bank_account.id,
        debit=0,
        credit=total_amount,
        description=f'سداد مستحقات الضريبة والزكاة'
    )
    db.session.add(detail3)

    db.session.commit()

    return {
        'success': True,
        'message': f'✅ تم تسجيل سداد ضريبة وزكاة سنة {year} بمبلغ {total_amount:,.2f} ريال',
        'entry_number': entry_number
    }




def print_salary_breakdown(breakdown):
    """طباعة تفاصيل توزيع الراتب"""
    print(f"\n{'=' * 50}")
    print(f"📊 توزيع راتب الموظف (الراتب الشامل: {breakdown['monthly_salary']:,.0f} ريال)")
    print(f"{'=' * 50}")
    print(f"   أيام الحضور: {breakdown['attendance_days']}")
    print(f"   نسبة الحضور: {breakdown['ratio']:.1%}")
    print(f"\n   💰 يصرف للعامل نقداً: {breakdown['cash_payout']:,.0f} ريال")
    print(f"      - الراتب الأساسي: {breakdown['basic_salary']:,.0f} ريال")
    print(f"      - بدل السكن: {breakdown['resident_allowance']:,.0f} ريال")
    print(f"\n   📋 يذهب كرصيد للشركة:")
    print(f"      - بدل الملابس: {breakdown['clothing_allowance']:,.0f} ريال")
    print(f"      - بطاقة صحية: {breakdown['health_card']:,.0f} ريال")
    print(f"      - تأمين: {breakdown['insurance']:,.0f} ريال")
    print(f"\n   📊 ربح المتعهد: {breakdown['contractor_profit']:,.0f} ريال")
    print(f"{'=' * 50}\n")


def calculate_worker_salary_breakdown(employee, attendance_days):
    """
    حساب توزيع الراتب للعامل حسب نظام شركة طلعت هائل
    """
    MONTHLY_WORK_DAYS = 30

    # المبالغ الثابتة
    BASE_WORKER_AMOUNT = 60000
    DAILY_RATE = BASE_WORKER_AMOUNT / MONTHLY_WORK_DAYS  # 2,000 ريال/يوم
    DAILY_RESIDENT = 500  # بدل السكن اليومي

    MONTHLY_CLOTHING = 2033.33
    MONTHLY_HEALTH = 1250.00
    MONTHLY_INSURANCE = 10800.00

    ratio = attendance_days / MONTHLY_WORK_DAYS if attendance_days > 0 else 0

    basic_payout = DAILY_RATE * attendance_days
    resident_payout = DAILY_RESIDENT * attendance_days
    cash_payout = basic_payout + resident_payout

    clothing_payout = MONTHLY_CLOTHING * ratio
    health_payout = MONTHLY_HEALTH * ratio
    insurance_payout = MONTHLY_INSURANCE * ratio

    difference = employee.salary - BASE_WORKER_AMOUNT
    contractor_profit = (difference * ratio) - (clothing_payout + health_payout + insurance_payout)

    return {
        'attendance_days': attendance_days,
        'ratio': ratio,
        'company_payment': employee.salary * ratio,
        'cash_payout': cash_payout,
        'basic_salary': basic_payout,
        'resident_allowance': resident_payout,
        'clothing_allowance': clothing_payout,
        'health_card': health_payout,
        'insurance': insurance_payout,
        'contractor_profit': contractor_profit,
        'monthly_salary': employee.salary
    }


def update_salary_with_breakdown(salary, breakdown):
    """تحديث كائن Salary بقيم التوزيع"""
    salary.basic_salary_amount = breakdown['basic_salary']
    salary.resident_allowance_amount = breakdown['resident_allowance']
    salary.clothing_allowance_amount = breakdown['clothing_allowance']
    salary.health_card_amount = breakdown['health_card']
    salary.insurance_amount = breakdown['insurance']
    salary.contractor_profit = breakdown['contractor_profit']
    salary.attendance_amount = breakdown['cash_payout']
    salary.total_salary = breakdown['cash_payout']
    return salary