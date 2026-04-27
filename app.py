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

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///talaat_company.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# تهيئة قاعدة البيانات
db.init_app(app)

# ✅ تحسين: التحقق من وجود الملف قبل استيراده

# ✅ تحسين: استيراد الإصلاح التلقائي للرواتب
try:
    import final_fix_all
    print("✅ تم تفعيل الإصلاح التلقائي للرواتب")
except ImportError:
    print("⚠️ final_fix_all غير موجود - سيتم تعطيل الإصلاح التلقائي")

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

# ✅ تحسين: المجدول التلقائي - يعمل فقط في بيئة التطوير
try:
    from apscheduler.schedulers.background import BackgroundScheduler

    def schedule_monthly_closing():
        """جدولة إقفال المصروفات في آخر يوم من كل شهر"""
        from utils import auto_close_expenses

        today = datetime.now().date()
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

    # تشغيل المجدول فقط في بيئة التطوير (وليس في Render)
    if not os.environ.get('RENDER') and 'gunicorn' not in sys.argv[0]:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=schedule_monthly_closing, trigger="interval", days=1)
        scheduler.start()
        print("✅ تم تشغيل المجدول التلقائي لإقفال المصروفات")
    else:
        print("ℹ️ تم تعطيل المجدول التلقائي في بيئة الإنتاج")

except ImportError:
    print("⚠️ مكتبة apscheduler غير مثبتة - تم تعطيل المجدول التلقائي")

# تسجيل جميع الروت
register_routes(app)

def init_db():
    """تهيئة قاعدة البيانات وإنشاء المستخدم admin"""
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

# ✅ تجنب تشغيل init_db() مرتين في بيئة الإنتاج
if not os.environ.get('RENDER_INITIALIZED'):
    init_db()
    os.environ['RENDER_INITIALIZED'] = 'true'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)