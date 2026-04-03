import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # استخدام رابط Supabase مباشرة
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres.jpuockjpxpvrlewvzahy:ali1993mubark@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ROLES = {
        'admin': 'مدير النظام',
        'supervisor': 'مشرف',
        'finance': 'موظف مالي',
        'viewer': 'مشاهد'
    }

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True