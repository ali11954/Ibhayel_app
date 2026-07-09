from .api import api_bp
from .rest_api import rest_api

ALL_BLUEPRINTS = [
    api_bp,
    rest_api,
]

def register_all_blueprints(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)