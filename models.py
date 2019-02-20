"""Python models defined"""
import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc

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


class Car(db.Model):
    """Car of a user"""
    __tablename__ = "cars"
    car_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("users.user_id"), nullable=False)
    car_name = db.Column(db.String(128), nullable=False)
    car_built = db.Column(db.Date, nullable=False)

    def est_mileage(self):
        """
        Returns the current estimated mileage based
        on the average over the life of the vehicle.
        """
        if not self.last_odometer():
            return

        age_days = (datetime.date.today() - self.car_built).days
        days_since_mileage = (datetime.date.today() - self.last_odometer().reading_date).days
        mpd = self.last_odometer().reading / age_days
        estimate = (mpd * days_since_mileage) + self.last_odometer().reading

        return int(estimate)

    def last_odometer(self):
        # Search for all odometer readings for the car. 
        # Show descending / only first
        odo = Odometer.query.filter(
            self.car_id == Odometer.car_id).order_by(
                Odometer.reading_id.desc()).first()
        return odo


class Odometer(db.Model):
    """Odometer reading for a car"""
    __tablename__ = "odometers"
    reading_id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.ForeignKey("cars.car_id"), nullable=False)
    reading = db.Column(db.Integer, nullable=False)
    reading_date = db.Column(db.Date, nullable=False)
