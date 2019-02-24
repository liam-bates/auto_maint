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
    maintenance = db.relationship(
        'Maintenance', cascade='all,delete', backref='vehicle')

    def est_mileage(self):
        """
        Returns the current estimated mileage by looking at the last odometer
        reading and comparing it to the age of the vehicle.
        """
        if not self.odo_readings:
            return 0

        if len(self.odo_readings) >= 2:
            second_last = self.odo_readings[-2]

        else:
            second_last = Odometer(reading=0, reading_date=self.vehicle_built)

        last = self.odo_readings[-1]
        days_between = (last.reading_date - second_last.reading_date).days
        miles_between = last.reading - second_last.reading
        mpd = miles_between / days_between
        days_since = (datetime.date.today() - last.reading_date).days
        estimate = (mpd * days_since) + last.reading

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

        # Find any odomete readings on the same date.
        same_date = Odometer.query.filter(self.vehicle_id == Odometer.vehicle_id).filter(new_reading.reading_date == Odometer.reading_date).first()
        if same_date:
            same_date.delete()

        # Write to DB
        db.session.add(new_reading)
        db.session.commit()

    def add_maintenance(self, name, description, freq_miles, freq_months):
        """ Method to add a maintenance event for the vehicle. """
        # Create a new maintenance object
        new_maintenance = Maintenance(
            vehicle_id=self.vehicle_id,
            name=name,
            description=description,
            freq_miles=freq_miles,
            freq_months=freq_months)

        # Write to DB
        db.session.add(new_maintenance)
        db.session.commit()

        return new_maintenance

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
        """ Returns the age of the vehicle in days."""

        today = datetime.date.today()
        age = (today - self.vehicle_built).days

        return age

    def status(self):

        vehicle_status = 'Good'

        for maintenance in self.maintenance:
            if maintenance.status() == 'Overdue':
                vehicle_status = 'Overdue'
                break
            if maintenance.status() == 'Maintenance Soon':
                vehicle_status = 'Maintenance Soon'

        return vehicle_status


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


class Maintenance(db.Model):
    """ A maintenance schedule for a vehicle. Represents a single task. """
    __tablename__ = "maintenance"
    maintenance_id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(
        db.ForeignKey("vehicles.vehicle_id"), nullable=False)
    name = db.Column(db.String(128), nullable=True)
    description = db.Column(db.String(256))
    freq_miles = db.Column(db.Integer, nullable=True)
    freq_months = db.Column(db.Integer, nullable=True)
    logs = db.relationship('Log', cascade='all,delete', backref='maintenance')

    def add_log(self, date, mileage, notes):
        """ Add a log entry for the maintenance schedule. """

        # Create a new maintenance object with user input
        new_log = Log(
            maintenance_id=self.maintenance_id,
            date=date,
            mileage=mileage,
            notes=notes)

        # Write to DB
        db.session.add(new_log)
        db.session.commit()

    def est_log(self):
        """ Generate a log entry for the maintenance schedule assuming 
        that the activity was undertaken in the past in accordance with the 
        maintenance schedule. """

        last_odo = self.vehicle.last_odometer().reading
        freq_days = (self.freq_months / 12) * 365.2524

        if self.freq_miles < last_odo or self.freq_months < (
                self.vehicle.age() * 12):
            new_log = Log(
                maintenance_id=self.maintenance_id,
                date=datetime.date.today() -
                datetime.timedelta(days=self.vehicle.age() % freq_days),
                mileage=last_odo - (last_odo % self.freq_miles),
                notes=
                'Autogenerated assuming reccomended maintenance schedule previously kept'
            )

            # Write to DB
            db.session.add(new_log)
            db.session.commit()

    def miles_until_due(self):
        #
        if not self.logs:
            miles_due = 0
        else:
            last_log = self.logs[-1]

            miles_due = self.freq_miles - (
                self.vehicle.est_mileage() - last_log.mileage)

            if miles_due < 0:
                miles_due = 0

        return miles_due

    def days_until_due(self):
        #
        if not self.logs:
            days_due = 0
        else:
            last_log = self.logs[-1]

            days_due = ((self.freq_months / 12) * 365.2524) - (
                datetime.date.today() - last_log.date).days

            if days_due < 0:
                days_due = 0

        return int(days_due)

    def status(self):

        days_due = self.days_until_due()
        miles_due = self.miles_until_due()

        if days_due == 0 or miles_due == 0:
            current_status = 'Overdue'

        elif days_due < 14 or miles_due < 500:
            current_status = 'Maintenance Soon'

        else:
            current_status = 'Good'

        return current_status


class Log(db.Model):
    """ Log of maintenance undertaken in a maintenance schedule."""
    __tablename__ = "logs"
    log_id = db.Column(db.Integer, primary_key=True)
    maintenance_id = db.Column(
        db.ForeignKey("maintenance.maintenance_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(256))
