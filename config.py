import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # استخدام Supabase PostgreSQL
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # استخدم رابط Supabase مباشرة (للاختبار المحلي)
        database_url = "postgresql://postgres.jpuockjpxpvrlewvzahy:YOUR_PASSWORD_HERE@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

    # تعديل الرابط لـ SQLAlchemy
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ROLES = {
        'admin': 'مدير النظام',
        'supervisor': 'مشرف',
        'finance': 'موظف مالي',
        'viewer': 'مشاهد'
    }

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'