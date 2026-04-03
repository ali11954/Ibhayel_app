from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

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
        'app_name': 'ابن هائل لأعمال الزراعة'
    }


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
# استدعاء init_db() عند بدء التطبيق (لـ gunicorn)
init_db()


if __name__ == '__main__':
    # استخدام PORT من متغيرات البيئة لـ Render
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)