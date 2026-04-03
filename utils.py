# utils.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


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
    from datetime import datetime, timedelta
    year, month = map(int, month_year.split('-'))

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

# utils.py
def get_regions():
    """الحصول على قائمة المناطق"""
    from models import Employee

    regions = Employee.query.with_entities(Employee.region).filter(
        Employee.region != None,
        Employee.region != ''
    ).distinct().all()
    return [r[0] for r in regions if r[0]]
