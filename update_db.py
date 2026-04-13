# update_db_company.py
import sqlite3

def update_database():
    try:
        # الاتصال بقاعدة البيانات - تأكد من اسم الملف الصحيح
        # جرب كلا الاسمين:
        # conn = sqlite3.connect('thaljat_alsaleef.db')
        conn = sqlite3.connect('ibn_hail.db')
        cursor = conn.cursor()

        # ✅ إضافة عمود criteria_scores إلى جدول evaluations
        try:
            cursor.execute("ALTER TABLE evaluations ADD COLUMN criteria_scores TEXT")
            print("✅ تم إضافة العمود criteria_scores إلى جدول evaluations")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ العمود criteria_scores موجود بالفعل")
            else:
                print(f"❌ خطأ في إضافة criteria_scores: {e}")

        # ✅ التأكد من وجود أعمدة min_score و max_score في evaluation_criteria
        try:
            cursor.execute("ALTER TABLE evaluation_criteria ADD COLUMN min_score INTEGER DEFAULT 0")
            print("✅ تم إضافة العمود min_score")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ العمود min_score موجود بالفعل")
            else:
                print(f"❌ خطأ: {e}")

        try:
            cursor.execute("ALTER TABLE evaluation_criteria ADD COLUMN max_score INTEGER DEFAULT 10")
            print("✅ تم إضافة العمود max_score")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ العمود max_score موجود بالفعل")
            else:
                print(f"❌ خطأ: {e}")

        conn.commit()
        conn.close()
        print("\n✅ تم تحديث قاعدة البيانات بنجاح")

    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    update_database()