"""Script to create DB"""
import os

from flask import Flask
from flask_session import Session

from models import DB

APP = Flask(__name__)


# Iniate DB / SQLAlchemy
APP.config["SQLALCHEMY_DATABASE_URI"] = os.environ['DATABASE_URL']
APP.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initiate session tracking type and create the sessions table
APP.config["SESSION_TYPE"] = "sqlalchemy"
SESSION = Session(APP)
SESSION.app.session_interface.db.create_all()

# Link the Flask app with the database (no Flask app is actually being run yet).
DB.init_app(APP)

# Initiate flask_session
SESSION = Session(APP)

def main():
    """ Execute main script to initiate DB. """
    # Create tables based on each table definition in `models`
    DB.create_all()

if __name__ == "__main__":
    # Allows for command line interaction with Flask application
    with APP.app_context():
        main()
