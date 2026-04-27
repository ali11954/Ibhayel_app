# reset_db.py
import os
import sys

# حذف قاعدة البيانات القديمة
db_files = ['app.db', 'app.db-journal', 'instance/app.db']
for f in db_files:
    if os.path.exists(f):
        os.remove(f)
        print(f"✅ تم حذف: {f}")

print("\n✅ تم حذف قاعدة البيانات القديمة")
print("🔄 أعد تشغيل التطبيق الآن باستخدام: python app.py")