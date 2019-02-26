"""Script to create DB"""

from flask import Flask
from flask_heroku import Heroku
from flask_session import Session

from models import db

app = Flask(__name__)

heroku = Heroku(app)

# Tell Flask what SQLAlchemy database to use.
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres://gpcqnmhwemexhc:3fffa4b61fbb9e381c7b3ac0b4f6494c195ae900767d43be77a29004c5d5bc73@ec2-23-21-130-182.compute-1.amazonaws.com:5432/d5bc43q580jbfr"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initiate session tracking type and create the sessions table
app.config["SESSION_TYPE"] = "sqlalchemy"
session = Session(app)
session.app.session_interface.db.create_all()

# Link the Flask app with the database (no Flask app is actually being run yet).
db.init_app(app)

# Initiate flask_session
session = Session(app)

def main():
    # Create tables based on each table definition in `models`
    db.create_all()

if __name__ == "__main__":
    # Allows for command line interaction with Flask application
    with app.app_context():
        main()
