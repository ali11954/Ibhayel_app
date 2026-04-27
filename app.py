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

try:
    import final_fix_all
    print("✅ تم تحميل final_fix_all")
except ImportError:
    print("⚠️ final_fix_all غير موجود")


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

# ... (بقية الكود الخاص بالمجدول والتسجيل والوظائف) ...

# تسجيل جميع الروت
register_routes(app)

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified")
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

# ✅ نقطة الدخول لتشغيل التطبيق (محليًا أو في الإنتاج)
# في الإنتاج، سيتولى Gunicorn بدء الخادم باستخدام الأمر `gunicorn app:app --bind 0.0.0.0:$PORT`
# محليًا، سيتم استخدام `python app.py`
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)