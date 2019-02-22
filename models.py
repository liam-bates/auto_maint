""" auto_maint app models defined """
import datetime
from dateutil.relativedelta import relativedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Define an object of a user within the context of the DB
class User(db.Model):
    """User of the website"""
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(93), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    failed_logins = db.Column(db.SmallInteger, default=0, nullable=False)
    blocked = db.Column(db.Boolean, default=False)
    vehicles = db.relationship('Vehicle', cascade='all,delete', backref='user')


class Vehicle(db.Model):
    """Vehicle of a user"""
    __tablename__ = "vehicles"
    vehicle_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("users.user_id"), nullable=False)
    vehicle_name = db.Column(db.String(128), nullable=False)
    vehicle_built = db.Column(db.Date, nullable=False)
    odo_readings = db.relationship(
        'Odometer', cascade='all,delete', backref='vehicle')
    schedules = db.relationship(
        'Schedule', cascade='all,delete', backref='vehicle')

    def est_mileage(self):
        """
        Returns the current estimated mileage by looking at the last odometer
        reading and comparing it to the age of the vehicle.
        """
        if not self.last_odometer():
            return 0

        print(len(self.odo_readings))

        age_at_reading = (
            self.last_odometer().reading_date - self.vehicle_built).days
        days_since_mileage = (
            datetime.date.today() - self.last_odometer().reading_date).days
        mpd = self.last_odometer().reading / age_at_reading
        estimate = (mpd * days_since_mileage) + self.last_odometer().reading

        return int(estimate)

    def last_odometer(self):
        """ Method to provide last odometer reading for the vehicle. """
        # Search for all odometer readings for the vehicle.
        # Show descending / only first
        odo = Odometer.query.filter(
            self.vehicle_id == Odometer.vehicle_id).order_by(
                Odometer.reading_id.desc()).first()
        return odo

    def add_odom_reading(self, mileage, date=datetime.date.today()):
        """ Method to add an odometer reading """
        new_reading = Odometer(
            vehicle_id=self.vehicle_id, reading=mileage, reading_date=date)
        # Write to DB
        db.session.add(new_reading)
        db.session.commit()

    def add(self):
        """ Method to save the current vehicle object to the DB. """
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """ Method to delete the current vehicle object from the DB. """
        db.session.delete(self)
        db.session.commit()

    def age(self):
        """ Returns the age of the vehicle in years."""

        today = datetime.date.today()
        age = today.year - self.vehicle_built.year - (
            (today.month, today.day) <
            (self.vehicle_built.month, self.vehicle_built.day))

        return age


class Odometer(db.Model):
    """ Odometer reading for a vehicle. """
    __tablename__ = "odometers"
    reading_id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(
        db.ForeignKey("vehicles.vehicle_id"), nullable=False)
    reading = db.Column(db.Integer, nullable=False)
    reading_date = db.Column(db.Date, nullable=False)

    def delete(self):
        """ Method to delete the odomter reading. """
        db.session.delete(self)


class Schedule(db.Model):
    """ A maintenance schedule for a vehicle. Represents a single task. """
    __tablename__ = "schedules"
    schedule_id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(
        db.ForeignKey("vehicles.vehicle_id"), nullable=False)
    schedule_name = db.Column(db.String(128), nullable=True)
    schedule_desc = db.Column(db.String(256))
    freq_miles = db.Column(db.Integer, nullable=True)
    freq_time = db.Column(db.Integer, nullable=True)
    log = db.relationship('Log', cascade='all,delete', backref='schedule')


class Log(db.Model):
    """ Log of maintenance undertaken in a maintenance schedule."""
    __tablename__ = "logs"
    log_id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(
        db.ForeignKey("schedules.schedule_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(256))
