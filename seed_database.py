# seed_database.py
from datetime import datetime, timedelta
import random
from models import db, Employee, Attendance, User, Company, Region, Location, FinancialTransaction
from werkzeug.security import generate_password_hash


def seed_database():
    """إدخال بيانات تجريبية للموظفين والحضور"""

    print("=" * 60)
    print("🚀 بدء إدخال البيانات التجريبية...")
    print("=" * 60)

    # ==================== 1. إنشاء الشركات ====================
    print("\n📌 1. إنشاء الشركات...")

    companies = [
        {'name': 'الشركة اليمنية لتكرير السكر', 'contact_person': 'أحمد محمد', 'phone': '+967 1 234567',
         'email': 'info@sugar.com'},
        {'name': 'شركة سبأ للزراعة', 'contact_person': 'علي حسن', 'phone': '+967 2 345678', 'email': 'info@sebaa.com'},
        {'name': 'مؤسسة هائل سعيد', 'contact_person': 'عبدالله عمر', 'phone': '+967 3 456789',
         'email': 'info@hail.com'},
    ]

    created_companies = []
    for comp_data in companies:
        company = Company.query.filter_by(name=comp_data['name']).first()
        if not company:
            company = Company(**comp_data)
            db.session.add(company)
            print(f"   ✅ تم إضافة شركة: {comp_data['name']}")
        else:
            print(f"   ⚠️ شركة موجودة: {comp_data['name']}")
        created_companies.append(company)

    db.session.commit()

    # ==================== 2. إنشاء المناطق والمواقع ====================
    print("\n📌 2. إنشاء المناطق والمواقع...")

    regions_data = [
        {'name': 'منطقة الحديدة', 'company_id': created_companies[0].id},
        {'name': 'منطقة صنعاء', 'company_id': created_companies[1].id},
        {'name': 'منطقة تعز', 'company_id': created_companies[2].id},
        {'name': 'منطقة عدن', 'company_id': created_companies[0].id},
    ]

    for reg_data in regions_data:
        region = Region.query.filter_by(name=reg_data['name'], company_id=reg_data['company_id']).first()
        if not region:
            region = Region(**reg_data)
            db.session.add(region)
            print(f"   ✅ تم إضافة منطقة: {reg_data['name']}")

    db.session.commit()

    # ==================== 3. إنشاء الموظفين ====================
    print("\n📌 3. إنشاء الموظفين...")

    employees_data = [
        # العمال - شركة السكر
        {'name': 'طلال أحمد', 'code': 'EMP001', 'card_number': 'CARD001',
         'job_title': 'عامل تسقية', 'region': 'الحديدة', 'is_resident': True,
         'phone': '771234567', 'salary': 60000, 'company_id': created_companies[0].id, 'employee_type': 'worker'},

        {'name': 'يوسف مهدي', 'code': 'EMP002', 'card_number': 'CARD002',
         'job_title': 'مشرف زراعة', 'region': 'الحديدة', 'is_resident': False,
         'phone': '772345678', 'salary': 80000, 'company_id': created_companies[0].id, 'employee_type': 'worker'},

        {'name': 'محمد علي', 'code': 'EMP003', 'card_number': 'CARD003',
         'job_title': 'عامل قص وتشكيل', 'region': 'الحديدة', 'is_resident': True,
         'phone': '773456789', 'salary': 55000, 'company_id': created_companies[0].id, 'employee_type': 'worker'},

        # عمال - شركة سبأ
        {'name': 'أحمد حسن', 'code': 'EMP004', 'card_number': 'CARD004',
         'job_title': 'عامل تسقية', 'region': 'صنعاء', 'is_resident': True,
         'phone': '774567890', 'salary': 58000, 'company_id': created_companies[1].id, 'employee_type': 'worker'},

        {'name': 'سعيد عبدالله', 'code': 'EMP005', 'card_number': 'CARD005',
         'job_title': 'مشرف', 'region': 'صنعاء', 'is_resident': False,
         'phone': '775678901', 'salary': 75000, 'company_id': created_companies[1].id, 'employee_type': 'worker'},

        # عمال - مؤسسة هائل
        {'name': 'خالد محمد', 'code': 'EMP006', 'card_number': 'CARD006',
         'job_title': 'عامل تسقية', 'region': 'تعز', 'is_resident': True,
         'phone': '776789012', 'salary': 60000, 'company_id': created_companies[2].id, 'employee_type': 'worker'},

        {'name': 'ناصر علي', 'code': 'EMP007', 'card_number': 'CARD007',
         'job_title': 'عامل قص', 'region': 'تعز', 'is_resident': False,
         'phone': '777890123', 'salary': 55000, 'company_id': created_companies[2].id, 'employee_type': 'worker'},

        # مشرفين
        {'name': 'مدير النظام', 'code': 'ADMIN001', 'card_number': 'CARDADMIN',
         'job_title': 'مدير عام', 'region': 'الحديدة', 'is_resident': False,
         'phone': '778901234', 'salary': 100000, 'company_id': None, 'employee_type': 'admin'},
    ]

    created_employees = []
    for emp_data in employees_data:
        employee = Employee.query.filter_by(code=emp_data['code']).first()
        if not employee:
            employee = Employee(**emp_data)
            db.session.add(employee)
            print(f"   ✅ تم إضافة موظف: {emp_data['name']} ({emp_data['job_title']})")
        else:
            print(f"   ⚠️ موظف موجود: {emp_data['name']}")
        created_employees.append(employee)

    db.session.commit()

    # ==================== 4. إنشاء المستخدمين للمشرفين ====================
    print("\n📌 4. إنشاء المستخدمين...")

    # مستخدم admin
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            full_name='مدير النظام',
            role='admin'
        )
        db.session.add(admin_user)
        print("   ✅ تم إضافة مستخدم admin")

    # ربط المشرفين بحسابات مستخدمين
    for emp in created_employees:
        if emp.employee_type in ['admin', 'supervisor'] and not emp.user_id:
            user = User.query.filter_by(username=emp.code.lower()).first()
            if not user:
                user = User(
                    username=emp.code.lower(),
                    password=generate_password_hash(emp.code.lower() + '123'),
                    full_name=emp.name,
                    role='supervisor' if emp.employee_type == 'supervisor' else 'admin'
                )
                db.session.add(user)
                db.session.flush()
                emp.user_id = user.id
                print(f"   ✅ تم إنشاء حساب للمشرف: {emp.name}")

    db.session.commit()

    # ==================== 5. إنشاء سجلات الحضور ====================
    print("\n📌 5. إنشاء سجلات الحضور للأشهر يناير، فبراير، مارس 2026...")

    # تواريخ الأشهر
    months = [
        {'name': 'يناير', 'year': 2026, 'month': 1, 'start': 1, 'end': 31},
        {'name': 'فبراير', 'year': 2026, 'month': 2, 'start': 1, 'end': 28},
        {'name': 'مارس', 'year': 2026, 'month': 3, 'start': 1, 'end': 31},
    ]

    attendance_statuses = ['present', 'absent', 'late', 'sick', 'annual_leave']
    status_weights = [0.7, 0.1, 0.1, 0.05, 0.05]  # 70% حضور، 10% غياب، 10% تأخير، 5% مرضية، 5% سنوية

    total_attendance = 0

    for month in months:
        print(f"\n   📅 معالجة شهر {month['name']} {month['year']}...")
        month_count = 0

        for day in range(month['start'], month['end'] + 1):
            current_date = datetime(month['year'], month['month'], day).date()

            # تخطي أيام الجمعة (اختياري - يمكن تعديلها)
            # if current_date.weekday() == 4:  # الجمعة
            #     continue

            for employee in created_employees:
                if employee.employee_type == 'admin':
                    continue

                # اختيار حالة عشوائية حسب الأوزان
                status = random.choices(attendance_statuses, weights=status_weights, k=1)[0]

                # معالجة الوقت للحضور والتأخير
                check_in_time = None
                check_out_time = None
                late_minutes = 0
                sick_leave_days = 0
                annual_leave_days = 0

                if status == 'present':
                    check_in_time = datetime.strptime(f"{random.randint(7, 9)}:{random.randint(0, 59)}", '%H:%M').time()
                    check_out_time = datetime.strptime(f"{random.randint(15, 17)}:{random.randint(0, 59)}",
                                                       '%H:%M').time()
                elif status == 'late':
                    check_in_time = datetime.strptime(f"{random.randint(9, 11)}:{random.randint(0, 59)}",
                                                      '%H:%M').time()
                    check_out_time = datetime.strptime(f"{random.randint(15, 17)}:{random.randint(0, 59)}",
                                                       '%H:%M').time()
                    late_minutes = random.randint(5, 60)
                elif status == 'sick':
                    sick_leave_days = 1
                elif status == 'annual_leave':
                    annual_leave_days = 1

                # التحقق من عدم وجود سجل مكرر
                existing = Attendance.query.filter_by(
                    employee_id=employee.id,
                    date=current_date
                ).first()

                if not existing:
                    attendance = Attendance(
                        employee_id=employee.id,
                        date=current_date,
                        attendance_type='individual',
                        attendance_status=status,
                        late_minutes=late_minutes,
                        sick_leave=(status == 'sick'),
                        sick_leave_days=sick_leave_days,
                        annual_leave_days=annual_leave_days,
                        check_in_time=check_in_time,
                        check_out_time=check_out_time,
                        notes=f"تسجيل آلي لشهر {month['name']}" if random.random() > 0.8 else None,
                        created_by=1  # admin user id
                    )
                    db.session.add(attendance)
                    month_count += 1
                    total_attendance += 1

        print(f"   ✅ تم إنشاء {month_count} سجل حضور لشهر {month['name']}")

    db.session.commit()
    print(f"\n   📊 إجمالي سجلات الحضور: {total_attendance}")

    # ==================== 6. إنشاء معاملات مالية تجريبية ====================
    print("\n📌 6. إنشاء معاملات مالية تجريبية...")

    transaction_types = ['advance', 'overtime', 'deduction', 'penalty']
    transaction_count = 0

    for employee in created_employees[:5]:  # أول 5 موظفين فقط
        for _ in range(random.randint(1, 3)):
            trans_type = random.choice(transaction_types)
            amount = random.choice([5000, 10000, 15000, 20000, 25000, 30000])

            if trans_type == 'advance':
                amount = random.choice([10000, 20000, 30000, 50000])
            elif trans_type == 'overtime':
                amount = random.choice([5000, 10000, 15000])
            elif trans_type in ['deduction', 'penalty']:
                amount = random.choice([2000, 5000, 10000])

            date = datetime(2026, random.randint(1, 3), random.randint(1, 25)).date()

            transaction = FinancialTransaction(
                employee_id=employee.id,
                transaction_type=trans_type,
                amount=amount,
                description=f"{'سلفة' if trans_type == 'advance' else 'إضافي' if trans_type == 'overtime' else 'خصم' if trans_type == 'deduction' else 'جزاء'} تجريبي",
                date=date,
                is_settled=False,
                created_by=1
            )
            db.session.add(transaction)
            transaction_count += 1

    db.session.commit()
    print(f"   ✅ تم إنشاء {transaction_count} معاملة مالية")

    # ==================== 7. إحصائيات نهائية ====================
    print("\n" + "=" * 60)
    print("📊 إحصائيات البيانات المدخلة:")
    print("=" * 60)
    print(f"   🏢 الشركات: {len(created_companies)}")
    print(f"   👥 الموظفين: {len(created_employees)}")
    print(f"   📅 سجلات الحضور: {total_attendance}")
    print(f"   💰 المعاملات المالية: {transaction_count}")
    print("=" * 60)
    print("\n🎉 تم إدخال البيانات التجريبية بنجاح!")
    print("\n📝 ملاحظات:")
    print("   - أيام الحضور: 70% من الأيام")
    print("   - أيام الغياب: 10%")
    print("   - أيام التأخير: 10%")
    print("   - إجازات مرضية: 5%")
    print("   - إجازات سنوية: 5%")
    print("\n🔑 بيانات الدخول:")
    print("   - المستخدم: admin")
    print("   - كلمة المرور: admin123")


if __name__ == '__main__':
    from app import app

    with app.app_context():
        seed_database()