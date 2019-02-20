"""Script to create DB"""

from flask import Flask
from flask_session import Session

from models import db

app = Flask(__name__)

# Tell Flask what SQLAlchemy database to use.
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://liambates:test@localhost/auto"
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
