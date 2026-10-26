"""Shared application setup. Business routes live in modules/module1–module3."""
import sys
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.vendor'))
from flask import Flask
from shared import db, hasher, init_app

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=str(ROOT/'instance'/'parceltrack.db'), UPLOADS=str(ROOT/'instance'/'proofs'), MAX_CONTENT_LENGTH=3*1024*1024, HTTPS=os.getenv('PARCELTRACK_HTTPS') == '1')
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOADS']).mkdir(parents=True, exist_ok=True)
    init_app(app)
    with app.app_context():
        db().executescript((ROOT/'database'/'schema.sql').read_text())
    from modules.module1 import bp as module1
    from modules.module2 import bp as module2
    from modules.module3 import bp as module3
    from pages import bp as pages
    for blueprint in (module1, module2, module3, pages):
        app.register_blueprint(blueprint)
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False)
