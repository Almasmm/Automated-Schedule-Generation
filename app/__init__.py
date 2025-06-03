from flask import Flask
from app.routes import bp
import os

def create_app():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(BASE_DIR, "templates")
    static_dir = os.path.join(BASE_DIR, "static")
    print("TEMPLATE DIR:", template_dir)
    app = Flask(__name__, static_folder=static_dir, template_folder=template_dir)
    app.register_blueprint(bp)
    return app
