import sqlite3
from datetime import datetime, timedelta

db_path = r'D:\ghith\binhayell\instance\talaat_company.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("📅 إضافة أيام حضور للموظفين - مارس 2026")
print("=" * 60)

# أولاً: معرفة هيكل جدول attendances
cursor.execute("PRAGMA table_info(attendances)")
columns = [col[1] for col in cursor.fetchall()]
print(f"\nأعمدة جدول attendances: {columns}")

# جلب الموظفين
cursor.execute("SELECT id, name FROM employees")
employees = cursor.fetchall()
print(f"\nالموظفون: {employees}")

# تحديد أيام العمل في أبريل 2026
start_date = datetime(2026, 3, 1)
end_date = datetime(2026, 3, 30)

# حذف الحضور القديم لشهر أبريل
cursor.execute("DELETE FROM attendances WHERE date BETWEEN '2026-03-01' AND '2026-03-30'")
print(f"🗑️ تم حذف الحضور القديم: {cursor.rowcount} سجل")

# إضافة حضور لكل موظف
attendance_count = 0
current_date = start_date

# معرفة اسم عمود الحالة (قد يكون status أو attendance_status)
status_column = 'status' if 'status' in columns else 'attendance_status' if 'attendance_status' in columns else 'is_present'

while current_date <= end_date:
    # تخطي يوم الجمعة (يوم 5 حيث Monday=0)
    if current_date.weekday() != 4:  # 4 = Friday
        for emp in employees:
            emp_id, name = emp
            try:
                cursor.execute(f"""
                    INSERT INTO attendances (employee_id, date, {status_column}, created_at)
                    VALUES (?, ?, 'present', datetime('now'))
                """, (emp_id, current_date.strftime('%Y-%m-%d')))
                attendance_count += 1
            except Exception as e:
                print(f"خطأ: {e}")
                # محاولة بدون created_at
                cursor.execute(f"""
                    INSERT INTO attendances (employee_id, date, {status_column})
                    VALUES (?, ?, 'present')
                """, (emp_id, current_date.strftime('%Y-%m-%d')))
                attendance_count += 1
    current_date += timedelta(days=1)

conn.commit()

print(f"\n✅ تم إضافة {attendance_count} سجل حضور")
if employees:
    print(f"📊 لكل موظف: {attendance_count // len(employees)} يوم حضور في مارس 2026")

# عرض ملخص الحضور
print("\n📋 ملخص الحضور:")
for emp in employees:
    emp_id, name = emp
    cursor.execute("SELECT COUNT(*) FROM attendances WHERE employee_id = ? AND date BETWEEN '2026-03-01' AND '2026-03-30'", (emp_id,))
    days = cursor.fetchone()[0]
    print(f"  {name}: {days} يوم")

conn.close()

print("\n" + "=" * 60)
print("✅ اكتمل! الآن اذهب إلى الرواتب الشهرية واضغط 'حساب الرواتب'")