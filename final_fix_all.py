from app import app
from models import db, Employee, Salary
from sqlalchemy import event


def fix_salary(salary):
    """تحديث راتب واحد بالقيم الصحيحة"""
    try:
        emp = Employee.query.get(salary.employee_id)
        if not emp:
            return False

        if emp.employee_type != 'worker':
            return False

        if salary.attendance_days == 0 or salary.attendance_days is None:
            return False

        # ========== المبالغ الثابتة الصحيحة ==========
        MONTHLY_DAYS = 30
        BASE_WORKER = 60000  # المبلغ المستحق للعامل لـ 30 يوم

        # القيم اليومية
        DAILY_RATE = BASE_WORKER / MONTHLY_DAYS  # 2,000 ريال/يوم
        DAILY_RESIDENT = 500  # بدل السكن اليومي

        # البدلات الشهرية
        CLOTHING_MONTHLY = 24400 / 12  # 2,033.33
        HEALTH_MONTHLY = 15000 / 12  # 1,250
        INSURANCE_MONTHLY = 10800  # 10,800

        days = salary.attendance_days
        ratio = days / MONTHLY_DAYS

        # حساب التوزيع
        basic = DAILY_RATE * days  # الراتب الأساسي
        resident = DAILY_RESIDENT * days  # بدل السكن
        cash = basic + resident  # المبلغ النقدي للعامل

        clothing = CLOTHING_MONTHLY * ratio  # بدل الملابس
        health = HEALTH_MONTHLY * ratio  # بطاقة صحية
        insurance = INSURANCE_MONTHLY * ratio  # تأمين

        diff = emp.salary - BASE_WORKER
        profit = (diff * ratio) - (clothing + health + insurance)

        # تحديث الراتب - التأكد من عدم وجود None
        salary.basic_salary_amount = basic or 0
        salary.resident_allowance_amount = resident or 0
        salary.clothing_allowance_amount = clothing or 0
        salary.health_card_amount = health or 0
        salary.insurance_amount = insurance or 0
        salary.contractor_profit = profit or 0
        salary.attendance_amount = cash or 0
        salary.total_salary = cash or 0

        print(f'   ✅ {emp.name}: {cash:,.0f} ريال (أساسي: {basic:,.0f} + سكن: {resident:,.0f})')
        print(f'      - بدل ملابس: {clothing:,.0f} ريال (24,400 سنوياً)')
        print(f'      - بطاقة صحية: {health:,.0f} ريال (15,000 سنوياً)')
        print(f'      - تأمين: {insurance:,.0f} ريال (10,800 شهرياً)')
        print(f'      - ربح المتعهد: {profit:,.0f} ريال')
        return True

    except Exception as e:
        print(f'   ❌ خطأ في تحديث راتب الموظف ID {salary.employee_id}: {str(e)}')
        return False


# استماع للأحداث - عند إضافة راتب جديد
@event.listens_for(Salary, 'before_insert')
def before_salary_insert(mapper, connection, target):
    print(f'\n🔧 إصلاح راتب جديد تلقائياً...')
    fix_salary(target)


# استماع للأحداث - عند تحديث راتب موجود
@event.listens_for(Salary, 'before_update')
def before_salary_update(mapper, connection, target):
    # فقط إذا كان الراتب لم يتم توزيعه بعد
    if target.basic_salary_amount == 0 or target.basic_salary_amount is None:
        print(f'\n🔧 إصلاح راتب محدث تلقائياً...')
        fix_salary(target)


def fix_all_existing_salaries():
    """تحديث جميع الرواتب الموجودة حالياً"""
    with app.app_context():
        print('\n' + '=' * 60)
        print('🔧 تحديث جميع الرواتب الموجودة...')
        print('=' * 60)

        salaries = Salary.query.all()
        count = 0
        for salary in salaries:
            if fix_salary(salary):
                count += 1
                db.session.add(salary)

        db.session.commit()
        print('=' * 60)
        print(f'✅ تم تحديث {count} راتب بنجاح')
        print('=' * 60)


# تشغيل التحديث عند تحميل الملف
with app.app_context():
    fix_all_existing_salaries()