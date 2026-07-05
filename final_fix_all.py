from app import app
from models import db, Employee, Salary
from sqlalchemy import event


def fix_salary(salary):
    """تحديث راتب واحد بالقيم الصحيحة - مع دعم خصم البوفية والمطعم"""
    try:
        emp = Employee.query.get(salary.employee_id)
        if not emp:
            return False

        # ========== معالجة العمال فقط ==========
        if emp.employee_type == 'worker':
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

            # ✅ فقط للساكنين
            if emp.is_resident:
                resident = DAILY_RESIDENT * days  # بدل السكن
            else:
                resident = 0

            cash = basic + resident  # المبلغ النقدي للعامل

            clothing = CLOTHING_MONTHLY * ratio
            health = HEALTH_MONTHLY * ratio
            insurance = INSURANCE_MONTHLY * ratio

            diff = emp.salary - BASE_WORKER
            profit = (diff * ratio) - (clothing + health + insurance)

            # تحديث الراتب
            salary.basic_salary_amount = basic or 0
            salary.resident_allowance_amount = resident or 0
            salary.clothing_allowance_amount = clothing or 0
            salary.health_card_amount = health or 0
            salary.insurance_amount = insurance or 0
            salary.contractor_profit = profit or 0
            salary.attendance_amount = cash or 0

            # ✅ المحافظة على خصم البوفية والمطعم إذا كان موجوداً
            # (لا نغيرها - نحافظ على القيم الحالية)

            # إعادة حساب الراتب النهائي مع مراعاة الخصومات
            total_deductions = (
                    (salary.advance_amount or 0) +
                    (salary.penalty_amount or 0) +
                    (salary.cafeteria_deduction or 0) +
                    (salary.restaurant_deduction or 0) +
                    (salary.meal_deduction or 0)
            )

            salary.total_salary = max(0, cash - total_deductions)

            print(
                f'   ✅ {emp.name} (عامل): {salary.total_salary:,.0f} ريال (أساسي: {basic:,.0f} + سكن: {resident:,.0f})')
            print(f'      - بدل ملابس: {clothing:,.0f} ريال')
            print(f'      - بطاقة صحية: {health:,.0f} ريال')
            print(f'      - تأمين: {insurance:,.0f} ريال')
            print(f'      - خصم بوفية: {salary.cafeteria_deduction or 0:,.0f} ريال')
            print(f'      - خصم مطعم: {salary.restaurant_deduction or 0:,.0f} ريال')
            print(f'      - ربح المتعهد: {profit:,.0f} ريال')
            return True

        # ========== معالجة المشرفين والإداريين ==========
        elif emp.employee_type in ['supervisor', 'admin']:
            if salary.attendance_days == 0 or salary.attendance_days is None:
                return False

            # حساب الراتب اليومي للمشرف/الإداري
            daily_rate = emp.salary / 30
            attendance_amount = daily_rate * salary.attendance_days

            # تطبيق الخصومات
            total_deductions = (
                    (salary.advance_amount or 0) +
                    (salary.penalty_amount or 0) +
                    (salary.cafeteria_deduction or 0) +
                    (salary.restaurant_deduction or 0)
            )

            salary.attendance_amount = attendance_amount
            salary.total_salary = max(0, attendance_amount - total_deductions)

            print(f'   ✅ {emp.name} ({emp.employee_type}): {salary.total_salary:,.0f} ريال')
            print(f'      - خصم بوفية: {salary.cafeteria_deduction or 0:,.0f} ريال')
            print(f'      - خصم مطعم: {salary.restaurant_deduction or 0:,.0f} ريال')
            return True

        return False

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