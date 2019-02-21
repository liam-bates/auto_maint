""" auto_maint app models defined """
import datetime

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
    cars = db.relationship('Car', cascade='all,delete', backref='user')


class Car(db.Model):
    """Car of a user"""
    __tablename__ = "cars"
    car_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("users.user_id"), nullable=False)
    car_name = db.Column(db.String(128), nullable=False)
    car_built = db.Column(db.Date, nullable=False)
    odo_readings = db.relationship(
        'Odometer', cascade='all,delete', backref='user')

    def est_mileage(self):
        """
        Returns the current estimated mileage by looking at the last odometer
        reading and comparing it to the age of the vehicle.
        """
        if not self.last_odometer():
            return 0

        print(len(self.odo_readings))

        age_at_reading = (
            self.last_odometer().reading_date - self.car_built).days
        days_since_mileage = (
            datetime.date.today() - self.last_odometer().reading_date).days
        mpd = self.last_odometer().reading / age_at_reading
        estimate = (mpd * days_since_mileage) + self.last_odometer().reading

        return int(estimate)

    def last_odometer(self):
        """ Method to provide last odometer reading for the vehicle. """
        # Search for all odometer readings for the car.
        # Show descending / only first
        odo = Odometer.query.filter(self.car_id == Odometer.car_id).order_by(
            Odometer.reading_id.desc()).first()
        return odo

    def add_odom_reading(self, mileage, date=datetime.date.today()):
        """ Method to add an odometer reading """
        new_reading = Odometer(
            car_id=self.car_id, reading=mileage, reading_date=date)
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


class Odometer(db.Model):
    """ Odometer reading for a vehicle. """
    __tablename__ = "odometers"
    reading_id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.ForeignKey("cars.car_id"), nullable=False)
    reading = db.Column(db.Integer, nullable=False)
    reading_date = db.Column(db.Date, nullable=False)

    def delete(self):
        """ Method to delete the odomter reading. """
        db.session.delete(self)
