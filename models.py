""" auto_maint app models defined """
import datetime

from flask_sqlalchemy import SQLAlchemy

DB = SQLAlchemy()


# Define an object of a user within the context of the DB
class User(DB.Model):
    """User of the website"""
    __tablename__ = "users"
    user_id = DB.Column(DB.Integer, primary_key=True)
    email = DB.Column(DB.String(256), unique=True, nullable=False)
    password_hash = DB.Column(DB.String(93), nullable=False)
    name = DB.Column(DB.String(128), nullable=False)
    failed_logins = DB.Column(DB.SmallInteger, default=0, nullable=False)
    blocked = DB.Column(DB.Boolean, default=False)
    vehicles = DB.relationship('Vehicle', cascade='all,delete', backref='user')


class Vehicle(DB.Model):
    """Vehicle of a user"""
    __tablename__ = "vehicles"
    vehicle_id = DB.Column(DB.Integer, primary_key=True)
    user_id = DB.Column(DB.ForeignKey("users.user_id"), nullable=False)
    vehicle_name = DB.Column(DB.String(128), nullable=False)
    vehicle_built = DB.Column(DB.Date, nullable=False)
    last_notification = DB.Column(DB.DateTime, nullable=True)
    odo_readings = DB.relationship(
        'Odometer', cascade='all,delete', backref='vehicle')
    maintenance = DB.relationship(
        'Maintenance', cascade='all,delete', backref='vehicle')

    def est_mileage(self):
        """
        Returns the current estimated mileage by looking at the last odometer
        reading and comparing it to the age of the vehicle.
        """
        sorted_odos = sorted(self.odo_readings, key=lambda x: x.reading_date)

        if not sorted_odos:
            return 0

        if len(sorted_odos) >= 2:
            second_last = sorted_odos[-2]

        else:
            second_last = Odometer(reading=0, reading_date=self.vehicle_built)

        last = sorted_odos[-1]
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
                Odometer.reading_date.desc()).first()
        return odo

    def add_odom_reading(self, mileage, date=datetime.date.today()):
        """ Method to add an odometer reading """
        new_reading = Odometer(
            vehicle_id=self.vehicle_id, reading=mileage, reading_date=date)

        # Find any odometer reading on the same date and delete it.
        same_date = Odometer.query.filter(
            self.vehicle_id == Odometer.vehicle_id).filter(
                new_reading.reading_date == Odometer.reading_date).first()
        if same_date:
            same_date.delete()

        # Write to DB
        DB.session.add(new_reading)
        DB.session.commit()

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
        DB.session.add(new_maintenance)
        DB.session.commit()

        return new_maintenance

    def add(self):
        """ Method to save the current vehicle object to the DB. """
        DB.session.add(self)
        DB.session.commit()
        return self

    def delete(self):
        """ Method to delete the current vehicle object from the DB. """
        DB.session.delete(self)
        DB.session.commit()

    def age(self):
        """ Returns the age of the vehicle in days."""

        today = datetime.date.today()
        age = (today - self.vehicle_built).days

        return age

    def status(self):
        """ Shows the status of the vehicle based on all of it's scheduled
        maintenance tasks. """

        vehicle_status = 'Good'

        for maintenance in self.maintenance:
            if maintenance.status() == 'Overdue':
                vehicle_status = 'Overdue'
                break
            if maintenance.status() == 'Soon':
                vehicle_status = 'Soon'

        return vehicle_status

    def notification_sent(self):
        self.last_notification = datetime.datetime.today()
        DB.session.commit()


class Odometer(DB.Model):
    """ Odometer reading for a vehicle. """
    __tablename__ = "odometers"
    reading_id = DB.Column(DB.Integer, primary_key=True)
    vehicle_id = DB.Column(
        DB.ForeignKey("vehicles.vehicle_id"), nullable=False)
    reading = DB.Column(DB.Integer, nullable=False)
    reading_date = DB.Column(DB.Date, nullable=False)

    def delete(self):
        """ Method to delete the odomter reading. """
        DB.session.delete(self)
        DB.session.commit()


class Maintenance(DB.Model):
    """ A maintenance schedule for a vehicle. Represents a single task. """
    __tablename__ = "maintenance"
    maintenance_id = DB.Column(DB.Integer, primary_key=True)
    vehicle_id = DB.Column(
        DB.ForeignKey("vehicles.vehicle_id"), nullable=False)
    name = DB.Column(DB.String(128), nullable=True)
    description = DB.Column(DB.String(256))
    freq_miles = DB.Column(DB.Integer, nullable=True)
    freq_months = DB.Column(DB.Integer, nullable=True)
    logs = DB.relationship('Log', cascade='all,delete', backref='maintenance')

    def add_log(self, date, mileage, notes):
        """ Add a log entry for the maintenance schedule. """

        # Create a new m;aintenance object with user input
        new_log = Log(
            maintenance_id=self.maintenance_id,
            date=date,
            mileage=mileage,
            notes=notes)

        # Add the mileage as an odometer reading.
        self.vehicle.add_odom_reading(mileage, date)

        # Write to DB
        DB.session.add(new_log)
        DB.session.commit()

    def est_log(self):
        """ Generate a log entry for the maintenance schedule assuming that the
        activity was undertaken in the past in accordance with the maintenance
        schedule. """

        last_odo = self.vehicle.last_odometer().reading
        freq_days = (self.freq_months / 12) * 365.2524

        if self.freq_miles < last_odo or freq_days < self.vehicle.age():
            new_log = Log(
                maintenance_id=self.maintenance_id,
                date=datetime.date.today() -
                datetime.timedelta(days=self.vehicle.age() % freq_days),
                mileage=last_odo - (last_odo % self.freq_miles),
                notes=
                'Autogenerated assuming reccomended maintenance schedule '\
                'previously kept.')

            # Write to DB
            DB.session.add(new_log)
            DB.session.commit()

    def miles_until_due(self):
        """ Shows the total miles based on current estimated mileage until
        maintenance task due. """

        # Calculated the miles since task last performed.
        miles_since = self.vehicle.est_mileage()
        sorted_logs = sorted(self.logs, key=lambda x: x.date)
        if sorted_logs:
            miles_since -= sorted_logs[-1].mileage

        # Calculate how many miles until due.
        miles_due = self.freq_miles - miles_since

        # If overdue show value as 0 instead of negative number
        if miles_due < 0:
            miles_due = 0

        # Return value
        return miles_due

    def days_until_due(self):
        """ Shows the total dauys until maintenance task due. """

        # If a previous log entry count days from there, otherwise use vehicle's
        # manufactured date
        sorted_logs = sorted(self.logs, key=lambda x: x.date)

        if sorted_logs:
            days_since = datetime.date.today() - sorted_logs[-1].date
        else:
            days_since = datetime.date.today() - self.vehicle.vehicle_built

        # Convert frequency to days and compare
        days_due = ((self.freq_months / 12) * 365.2524) - days_since.days

        # If overdue return 0 as opposed to negative
        if days_due < 0:
            days_due = 0

        # Return value as an integer.
        return int(days_due)

    def status(self):
        """
        Check the status of the maintenance task.

        Returns 'Good' if not due within 500 miles or 14 days.
        Returns 'Soon' if due within 500 miles or 14 days.
        Returns 'Overdue' if due within 0 miles or 0 days.
        """
        # Check the number of days and miles until due.
        days_due = self.days_until_due()
        miles_due = self.miles_until_due()

        # Check if Overdue
        if days_due == 0 or miles_due == 0:
            current_status = 'Overdue'
        # Check if Soon
        elif days_due < 14 or miles_due < 500:
            current_status = 'Soon'
        # Otherwise treat as Good
        else:
            current_status = 'Good'
        # Return finding
        return current_status

    def delete(self):
        """ Method to delete the maintenance task. """
        DB.session.delete(self)
        DB.session.commit()


class Log(DB.Model):
    """ Log of maintenance undertaken in a maintenance schedule."""
    __tablename__ = "logs"
    log_id = DB.Column(DB.Integer, primary_key=True)
    maintenance_id = DB.Column(
        DB.ForeignKey("maintenance.maintenance_id"), nullable=False)
    date = DB.Column(DB.Date, nullable=False)
    mileage = DB.Column(DB.Integer, nullable=True)
    notes = DB.Column(DB.String(256))

    def delete(self):
        """ Method to delete the log. """
        DB.session.delete(self)
        DB.session.commit()
