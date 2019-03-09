import datetime
from email.message import EmailMessage

from flask import render_template

from auto_maint import app
from auto_maint.helpers import send_email
from auto_maint.models import User


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
                    send_email(msg)

                    # Update DB to with timestamp
                    user_vehicle.notification_sent()
