""" Web app to save maintenance schedule of a users vehicle. """
import atexit
import os

from apscheduler.schedulers.background import BackgroundScheduler
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

from auto_maint.helpers import notify_users
import auto_maint.views

# Setup scheduler for to check if users need a notification every 5 minutes
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=notify_users, trigger="interval", minutes=5)
    scheduler.start()

    atexit.register(lambda: scheduler.shutdown())
