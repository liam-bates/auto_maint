""" Helpful functions used in the auto_maint app. """
import os
import smtplib
from functools import wraps

from flask import redirect, session


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


def send_email(message):
    """ Sends the provided email message using SMTP. """
    # Send message to the email server.
    server = smtplib.SMTP(os.environ['SMTP_SERVER'])
    server.starttls()
    server.login(os.environ['SMTP_LOGIN'], os.environ['SMTP_PASSWORD'])
    server.send_message(message)
    server.quit()


def standard_schedule(vehicle):
    # Based on a 2001 Honda Accord
    vehicle.add_maintenance(
        'Replace Engine Oil',
        "Check your vehicle's manual to determine the correct oil type.", 7500,
        12)
    vehicle.add_maintenance('Replace Oil Filter', '', 15000, 12)
    vehicle.add_maintenance('Replace Air Cleaner Element', '', 30000, 24)
    vehicle.add_maintenance('Inspect Valve Clearance', 'Adjust if noisy.',
                            105000, 84)
    vehicle.add_maintenance('Replace Spark Plugs', '', 105000, 84)
    vehicle.add_maintenance('Replace Timing Belt', '', 105000, 84)
    vehicle.add_maintenance('Replace Balancer Belt', '', 105000, 84)
    vehicle.add_maintenance('Inspect Water Pump', '', 105000, 84)
    vehicle.add_maintenance('Inspect and Adjust Drive Belts', '', 30000, 24)
    vehicle.add_maintenance('Inspect Idle Speed', '', 105000, 84)
    vehicle.add_maintenance('Replace Engine Coolant', '', 120000, 120)
    vehicle.add_maintenance('Replace Transmission Fluid', '', 120000, 72)
    vehicle.add_maintenance('Inspect Front and Rear Brakes', '', 15000, 12)
    vehicle.add_maintenance('Replace Brake Fluid', '', 45000, 36)
    vehicle.add_maintenance('Check Parking Brake Adjustment', '', 15000, 12)
    vehicle.add_maintenance('Replace Air Conditioning Filter', '', 30000, 24)
    vehicle.add_maintenance(
        'Rotate Tires',
        'Check tire inflation and condition at least once per month.', 15000,
        12)

    # Add estimated logs for the new maintenance events.
    for maintenance in vehicle.maintenance:
        maintenance.est_log()
