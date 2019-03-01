""" Web app to save maintenance schedule of a users vehicle. """
import os

from flask import Flask, session
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# DB Configs
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ['DATABASE_URL']
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initiate DB
db = SQLAlchemy(app)

# Initiate session tracking type
app.config["SESSION_TYPE"] = "sqlalchemy"
mksess = Session(app)
mksess.app.session_interface.db.create_all()

# Initiate Flask-Migrate
migrate = Migrate(app, db)

# Set domain
app.config["SERVER_NAME"] = os.environ['SERVER_NAME']

import auto_maint.views

# Stop reloader process
if __name__ == '__main__':
    app.run(use_reloader=False)
