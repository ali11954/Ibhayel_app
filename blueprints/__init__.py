from .api import api_bp
from .rest_api import rest_api
from .biometric import biometric_bp

ALL_BLUEPRINTS = [
    api_bp,
    rest_api,
    biometric_bp,
]

def register_all_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)