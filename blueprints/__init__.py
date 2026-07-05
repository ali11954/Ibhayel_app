from .auth import auth
from .employees import employees_bp
from .attendance import attendance_bp
from .companies import companies_bp
from .evaluations import evaluations_bp
from .financial import financial_bp
from .accounts import accounts_bp
from .suppliers import suppliers_bp
from .reports import reports_bp
from .labor import labor_bp
from .settings import settings_bp
from .api import api_bp
from .rest_api import rest_api

ALL_BLUEPRINTS = [
    auth,
    employees_bp,
    attendance_bp,
    companies_bp,
    evaluations_bp,
    financial_bp,
    accounts_bp,
    suppliers_bp,
    reports_bp,
    labor_bp,
    settings_bp,
    api_bp,
    rest_api,
]

def register_all_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)