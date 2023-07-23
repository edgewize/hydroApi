from flask import Flask
import hydrofunctions as hf

def create_app():
    app = Flask(__name__)
#    hf.NWIS = hf.NWIS()  # Initialize the hydrofunctions library

    from . import routes
    app.register_blueprint(routes.bp)

    return app
