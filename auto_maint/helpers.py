""" Helpful functions used in the auto_maint app. """
import datetime
import os
import smtplib
from email.message import EmailMessage
from functools import wraps

from flask import redirect, render_template, session

from auto_maint import app
from auto_maint.models import User

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function

def email(message):
    """ Sends the provided email message using SMTP. """
    # Send message to the email server.
    server = smtplib.SMTP(os.environ['SMTP_SERVER'])
    server.starttls()
    server.login(os.environ['SMTP_LOGIN'], os.environ['SMTP_PASSWORD'])
    server.send_message(message)
    server.quit()

def notify_users():
    """  Routine script to send email notifications when a vehicle is overdue
    maintenance. """
    # Context to access DB from function
    with app.app_context():
        print("NOTIFY USERS RUNNING")
        for user in User.query.all():
            for user_vehicle in user.vehicles:
                status = user_vehicle.status()
                if 'Soon' in status or 'Overdue' in status:
                    if user_vehicle.last_notification:
                        days_since = datetime.datetime.today(
                        ) - user_vehicle.last_notification
                        if days_since < datetime.timedelta(days=3):
                            continue

                    # Generate Email message to send
                    msg = EmailMessage()
                    msg['Subject'] = 'Your vehicle is due maintenance'
                    msg['From'] = 'auto_maint@liam-bates.com'
                    msg['To'] = user.email

                    # Generate HTML for email
                    html = render_template(
                        'email/reminder.html', vehicle=user_vehicle)
                    msg.set_content(html, subtype='html')

                    # Send email
                    email(msg)

                    # Update DB to with timestamp
                    user_vehicle.notification_sent()
