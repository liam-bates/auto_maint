""" Web app to save maintenance schedule of a users vehicle. """
import os

from flask import Flask, session
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)

# DB Configs
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ['DATABASE_URL']
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initiate DB
db = SQLAlchemy(app)

# Initiate session tracking type
app.config["SESSION_TYPE"] = "sqlalchemy"
sess = Session(app)
sess.app.session_interface.db.create_all()

# Initiate Flask-Migrate
migrate = Migrate(app, db)

# Set domain
app.config["SERVER_NAME"] = os.environ['SERVER_NAME']

# Set secret key
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

# Set timed serializer
ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])

csrf = CSRFProtect(app)

import auto_maint.views
