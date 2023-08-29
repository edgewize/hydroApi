from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
  

app = Flask(__name__)


db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hydro.db"
    db.init_app(app)

    CORS(app)

    from . import routes

    app.register_blueprint(routes.bp)

    return app
