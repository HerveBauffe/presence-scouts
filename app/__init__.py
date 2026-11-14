import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import timedelta

db = SQLAlchemy()
login_manager = LoginManager()

# Configuration des cookies de connexion
class Config:
    SECRET_KEY = "Ceci est la clé de connexion Atlantide Ultra Secrète"
    REMEMBER_COOKIE_DURATION = timedelta(days=60)

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Configuration (change SECRET_KEY en production)
    app.config.from_mapping(
        SECRET_KEY="change_this_super_secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "database.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # crée instance/ et uploads/ si besoin
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    # les routes et models sont importés ici (après init des extensions)
    from . import routes, models  # noqa: F401

    app.register_blueprint(routes.bp)

    # crée les tables en DB si besoin
    with app.app_context():
        db.create_all()

    return app
