# update_db_company.py
import sqlite3


def update_database():
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect('ibn_hail.db')
        cursor = conn.cursor()

        # إضافة عمود company_id إلى جدول employees إذا لم يكن موجوداً
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN company_id INTEGER REFERENCES companies(id)")
            print("✅ تم إضافة العمود company_id إلى جدول employees")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ العمود company_id موجود بالفعل")
            else:
                print(f"❌ خطأ: {e}")

        # إضافة الأعمدة الجديدة إلى جدول attendances (إذا لم تكن موجودة)
        attendance_columns = [
            "attendance_status VARCHAR(20) DEFAULT 'present'",
            "late_minutes INTEGER DEFAULT 0",
            "sick_leave BOOLEAN DEFAULT 0",
            "sick_leave_days INTEGER DEFAULT 0",
            "check_in_time TIME",
            "check_out_time TIME",
            "notes TEXT"
        ]

        for column in attendance_columns:
            try:
                cursor.execute(f"ALTER TABLE attendances ADD COLUMN {column}")
                print(f"✅ تم إضافة العمود إلى attendances: {column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"⚠️ العمود موجود بالفعل: {column}")
                else:
                    print(f"❌ خطأ في {column}: {e}")

        conn.commit()
        conn.close()
        print("\n✅ تم تحديث قاعدة البيانات بنجاح")

    except Exception as e:
        print(f"❌ خطأ: {e}")


if __name__ == '__main__':
    update_database()