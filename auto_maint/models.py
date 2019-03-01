""" auto_maint app models defined """
import datetime

from auto_maint import db


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
    last_notification = db.Column(db.DateTime, nullable=True)
    odo_readings = db.relationship(
        'Odometer', cascade='all,delete', backref='vehicle')
    maintenance = db.relationship(
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
        """ Records when notifcation has been sent. """
        self.last_notification = datetime.datetime.today()
        db.session.commit()


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
        db.session.commit()


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

        # Create a new m;aintenance object with user input
        new_log = Log(
            maintenance_id=self.maintenance_id,
            date=date,
            mileage=mileage,
            notes=notes)

        # Add the mileage as an odometer reading.
        self.vehicle.add_odom_reading(mileage, date)

        # Write to DB
        db.session.add(new_log)
        db.session.commit()

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
                'Autogenerated assuming recommended maintenance schedule '\
                'previously kept.')

            # Write to DB
            db.session.add(new_log)
            db.session.commit()

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
        db.session.delete(self)
        db.session.commit()


class Log(db.Model):
    """ Log of maintenance undertaken in a maintenance schedule."""
    __tablename__ = "logs"
    log_id = db.Column(db.Integer, primary_key=True)
    maintenance_id = db.Column(
        db.ForeignKey("maintenance.maintenance_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    mileage = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(256))

    def delete(self):
        """ Method to delete the log. """
        db.session.delete(self)
        db.session.commit()
