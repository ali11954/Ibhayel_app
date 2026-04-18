from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import os
import sys

from config import Config
from models import db, User
from routes import register_routes

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config.from_object(Config)

# تكوين قاعدة البيانات لـ Render
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///talaat_company.db'

# تهيئة قاعدة البيانات
db.init_app(app)

# تهيئة Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# إضافة متغيرات عامة لجميع القوالب
@app.context_processor
def utility_processor():
    return {
        'now': datetime.now(),
        'app_name': 'طلعت هائل للخدمات والاستشارات الزراعية'
    }


# محاولة استيراد المجدول (مع التعامل مع الخطأ إذا لم تكن المكتبة مثبتة)
try:
    from apscheduler.schedulers.background import BackgroundScheduler


    def schedule_monthly_closing():
        """جدولة إقفال المصروفات في آخر يوم من كل شهر"""
        from utils import auto_close_expenses

        today = datetime.now().date()
        # حساب أول يوم من الشهر القادم
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        is_last_day = (next_month - timedelta(days=1)) == today

        if is_last_day:
            print(f"📆 اليوم {today} هو آخر يوم في الشهر - جاري إقفال المصروفات...")
            try:
                auto_close_expenses()
                print("✅ تم إقفال المصروفات تلقائياً")
            except Exception as e:
                print(f"❌ خطأ في إقفال المصروفات: {e}")


    # تشغيل المجدول - فقط إذا لم يكن في بيئة Render (لتجنب عمليات متعددة)
    if 'gunicorn' not in sys.argv[0] and 'waitress' not in sys.argv[0]:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=schedule_monthly_closing, trigger="interval", days=1)
        scheduler.start()
        print("✅ تم تشغيل المجدول التلقائي لإقفال المصروفات")
    else:
        print("ℹ️ تم تعطيل المجدول التلقائي في بيئة الإنتاج")

except ImportError:
    print("⚠️ مكتبة apscheduler غير مثبتة - تم تعطيل المجدول التلقائي")
    print("   للتثبيت: pip install apscheduler")

# تسجيل جميع الروت
register_routes(app)


def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified")

        # إنشاء أو تحديث مستخدم admin
        admin = User.query.filter_by(username='admin').first()

        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                full_name='مدير النظام',
                role='admin'
            )
            db.session.add(admin)
            print("✅ تم إنشاء المستخدم admin")
        else:
            admin.password = generate_password_hash('admin123')
            print("✅ تم تحديث كلمة مرور admin")

        db.session.commit()


# استدعاء init_db() عند بدء التطبيق
init_db()

if __name__ == '__main__':
    # استخدام PORT من متغيرات البيئة لـ Render
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)