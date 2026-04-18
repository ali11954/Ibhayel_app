# seed_transactions.py
from datetime import datetime, timedelta
import random
from models import db, Employee, FinancialTransaction


def seed_transactions():
    """إدخال معاملات مالية تجريبية لأربعة أشهر"""

    print("=" * 60)
    print("💰 بدء إدخال المعاملات المالية التجريبية...")
    print("=" * 60)

    # ==================== 1. الحصول على الموظفين ====================
    employees = Employee.query.filter(Employee.employee_type == 'worker').all()
    if not employees:
        print("❌ لا توجد موظفين في قاعدة البيانات")
        return

    print(f"\n📌 الموظفين المتاحين: {len(employees)}")

    # ==================== 2. تعريف الأشهر ====================
    months = [
        {'name': 'يناير', 'year': 2026, 'month': 1, 'days': 31, 'start': 1, 'end': 31},
        {'name': 'فبراير', 'year': 2026, 'month': 2, 'days': 28, 'start': 1, 'end': 28},
        {'name': 'مارس', 'year': 2026, 'month': 3, 'days': 31, 'start': 1, 'end': 31},
        {'name': 'أبريل', 'year': 2026, 'month': 4, 'days': 30, 'start': 1, 'end': 30},
    ]

    # أنواع المعاملات وإعداداتها
    transaction_configs = {
        'advance': {
            'name': 'سلفة',
            'amount_range': (5000, 50000),
            'amount_step': 5000,
            'probability': 0.3,  # 30% من الموظفين في الشهر
            'icon': '💰',
            'color': 'warning'
        },
        'overtime': {
            'name': 'إضافي',
            'amount_range': (1000, 15000),
            'amount_step': 1000,
            'probability': 0.4,
            'icon': '⏰',
            'color': 'success'
        },
        'deduction': {
            'name': 'خصم',
            'amount_range': (500, 10000),
            'amount_step': 500,
            'probability': 0.25,
            'icon': '📉',
            'color': 'danger'
        },
        'penalty': {
            'name': 'جزاء',
            'amount_range': (200, 5000),
            'amount_step': 200,
            'probability': 0.15,
            'icon': '⚠️',
            'color': 'dark'
        }
    }

    total_transactions = 0
    transaction_details = []

    # ==================== 3. إنشاء المعاملات لكل شهر ====================
    print("\n📌 إنشاء المعاملات المالية...")

    for month in months:
        print(f"\n   📅 شهر {month['name']} {month['year']}:")
        month_count = 0

        for employee in employees:
            # لكل موظف، احتمالية وجود معاملات في هذا الشهر
            for trans_type, config in transaction_configs.items():
                # تحديد إذا كان سيتم إضافة معاملة من هذا النوع
                if random.random() < config['probability']:
                    # عدد المعاملات لهذا النوع في الشهر (1-3)
                    num_trans = random.randint(1, 2)

                    for _ in range(num_trans):
                        # تحديد المبلغ
                        min_amt, max_amt = config['amount_range']
                        step = config['amount_step']
                        amount = random.randrange(min_amt, max_amt + step, step)

                        # تاريخ عشوائي في الشهر
                        day = random.randint(month['start'], month['end'])
                        date = datetime(month['year'], month['month'], day).date()

                        # وصف المعاملة
                        descriptions = {
                            'advance': [
                                f"سلفة شهر {month['name']}",
                                f"طلب سلفة للمصروفات",
                                f"سلفة عاجلة",
                                f"دفعة مقدمة",
                            ],
                            'overtime': [
                                f"ساعات إضافية شهر {month['name']}",
                                f"عمل إضافي نهاية الأسبوع",
                                f"ساعات إضافية - مشروع خاص",
                                f"أعمال إضافية موثقة",
                            ],
                            'deduction': [
                                f"خصم شهر {month['name']}",
                                f"خصم على الغياب",
                                f"خصم تأخير",
                                f"استقطاع",
                            ],
                            'penalty': [
                                f"جزاء إداري شهر {month['name']}",
                                f"غرامة تأخير",
                                f"مخالفة نظام العمل",
                                f"جزاء إجراءات",
                            ]
                        }

                        description = random.choice(descriptions[trans_type])

                        # إنشاء المعاملة
                        transaction = FinancialTransaction(
                            employee_id=employee.id,
                            transaction_type=trans_type,
                            amount=amount,
                            description=description,
                            date=date,
                            is_settled=False,  # غير مسواة بعد
                            created_by=1  # admin user
                        )
                        db.session.add(transaction)
                        month_count += 1
                        total_transactions += 1

                        transaction_details.append({
                            'month': month['name'],
                            'employee': employee.name,
                            'type': config['name'],
                            'amount': amount,
                            'date': date
                        })

        print(f"      ✅ تم إنشاء {month_count} معاملة")

    db.session.commit()

    # ==================== 4. عرض الإحصائيات ====================
    print("\n" + "=" * 60)
    print("📊 إحصائيات المعاملات المالية المدخلة:")
    print("=" * 60)

    # إحصائيات حسب النوع
    stats_by_type = {}
    for detail in transaction_details:
        trans_type = detail['type']
        if trans_type not in stats_by_type:
            stats_by_type[trans_type] = {'count': 0, 'total': 0}
        stats_by_type[trans_type]['count'] += 1
        stats_by_type[trans_type]['total'] += detail['amount']

    for trans_type, stats in stats_by_type.items():
        print(f"   {trans_type}: {stats['count']} معاملة - {stats['total']:,.0f} ر.ي")

    # إحصائيات حسب الشهر
    print("\n📅 حسب الشهر:")
    months_stats = {}
    for detail in transaction_details:
        month = detail['month']
        if month not in months_stats:
            months_stats[month] = {'count': 0, 'total': 0}
        months_stats[month]['count'] += 1
        months_stats[month]['total'] += detail['amount']

    for month, stats in months_stats.items():
        print(f"   {month}: {stats['count']} معاملة - {stats['total']:,.0f} ر.ي")

    print("\n" + "=" * 60)
    print(f"🎉 تم إدخال {total_transactions} معاملة مالية بنجاح!")
    print("=" * 60)

    # ==================== 5. عرض عينة من المعاملات ====================
    print("\n📋 عينة من المعاملات المضافة:")
    print("-" * 60)
    for i, detail in enumerate(transaction_details[:10]):
        print(
            f"   {i + 1}. {detail['employee']} - {detail['type']}: {detail['amount']:,.0f} ر.ي - {detail['date'].strftime('%Y-%m-%d')}")

    if len(transaction_details) > 10:
        print(f"   ... و {len(transaction_details) - 10} معاملة أخرى")

    return total_transactions


def seed_additional_transactions():
    """إضافة معاملات إضافية لبعض الموظفين بشكل محدد"""

    print("\n" + "=" * 60)
    print("💰 إضافة معاملات إضافية محددة...")
    print("=" * 60)

    # البحث عن موظفين محددين
    employee1 = Employee.query.filter_by(name='طلال أحمد').first()
    employee2 = Employee.query.filter_by(name='يوسف مهدي').first()

    if not employee1 or not employee2:
        print("⚠️ لم يتم العثور على الموظفين المطلوبين")
        return

    additional_transactions = [
        # سلف كبيرة للموظف الأول
        {
            'employee_id': employee1.id,
            'transaction_type': 'advance',
            'amount': 50000,
            'description': 'سلفة لشراء سيارة',
            'date': datetime(2026, 2, 15).date()
        },
        # إضافي كبير للموظف الثاني
        {
            'employee_id': employee2.id,
            'transaction_type': 'overtime',
            'amount': 25000,
            'description': 'ساعات إضافية استثنائية',
            'date': datetime(2026, 3, 20).date()
        },
        # خصم
        {
            'employee_id': employee1.id,
            'transaction_type': 'deduction',
            'amount': 5000,
            'description': 'خصم بسبب الغياب',
            'date': datetime(2026, 4, 10).date()
        },
        # جزاء
        {
            'employee_id': employee2.id,
            'transaction_type': 'penalty',
            'amount': 2000,
            'description': 'جزاء تأخير',
            'date': datetime(2026, 1, 25).date()
        },
    ]

    for trans_data in additional_transactions:
        existing = FinancialTransaction.query.filter_by(
            employee_id=trans_data['employee_id'],
            transaction_type=trans_data['transaction_type'],
            amount=trans_data['amount'],
            date=trans_data['date']
        ).first()

        if not existing:
            transaction = FinancialTransaction(**trans_data, is_settled=False, created_by=1)
            db.session.add(transaction)
            print(f"   ✅ تم إضافة معاملة: {trans_data['description']} - {trans_data['amount']:,.0f} ر.ي")

    db.session.commit()
    print("\n✅ تم إضافة المعاملات الإضافية")


if __name__ == '__main__':
    from app import app

    with app.app_context():
        # حذف المعاملات القديمة (اختياري)
        # FinancialTransaction.query.delete()
        # db.session.commit()
        # print("🗑️ تم حذف المعاملات القديمة")

        # إضافة المعاملات الجديدة
        total = seed_transactions()
        seed_additional_transactions()

        print("\n🎉 اكتمل إدخال المعاملات المالية!")