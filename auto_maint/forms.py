from datetime import date

from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash
from wtforms import (BooleanField, PasswordField, StringField, ValidationError,
                     HiddenField, SubmitField)
from wtforms.fields.html5 import DateField, IntegerField
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                NumberRange)

from auto_maint.models import User, Vehicle


def available(form, field):
    # Ensure no other registered users have that email
    if User.query.filter(User.email == field.data).count():
        raise ValidationError('Email already registered.')


def user_authenticate(form, field):
    """ Ensure user exists, is not blocked and that the provided password was
    correct. """
    # Query the DB for a matching email address and save it as user object
    user = User.query.filter(User.email == field.data).first()

    # Check if user exists
    if user:
        # Check if account blocked
        if user.blocked:
            raise ValidationError('Account Blocked.')
    else:
        raise ValidationError('Unknown Email provided.')


def pw_authenticate(form, field):
    user = User.query.filter(User.email == form.email.data).first()
    # Check if User known
    if user:
        # Check if password correct
        if not check_password_hash(user.password_hash, field.data):
            # Record a failed login
            user.failed_login()
            raise ValidationError('Incorrect password provided.')
        # Record a succesful login
        else:
            user.successful_login()


def logical_date(form, field):
    """ Ensure provided date isn't in the future or prior to 1900. """
    if field.data > date.today():
        raise ValidationError('Date cannot be in the future.')
    if field.data < date(1900, 1, 1):
        raise ValidationError('Date cannot be earlier than year 1900.')


def greater_odometer(form, field):
    """ Ensure odometer reading provided is higher than most recent. """
    print(form.vehicle.data)
    # Ensure that new mileage is higher than previous
    if field.data < form.vehicle.data.last_odometer().reading:
        raise ValidationError(
            'New mileage reading must be higher than a previous reading.')


class RegistrationForm(FlaskForm):
    """ Registration form for a new user. """
    email = StringField(
        'Email',
        validators=[DataRequired(),
                    Email(),
                    Length(5, 256), available],
        description='Your Email')
    name = StringField(
        'Name',
        validators=[DataRequired(), Length(2, 64)],
        description='Your Name')
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(6, 64),
            EqualTo('confirm', 'Password and confirmation do not match.')
        ],
        description='Password')
    confirm = PasswordField(
        validators=[DataRequired()], description='Confirm Password')


class LoginForm(FlaskForm):
    """ Form to login app users. """
    email = StringField(
        'Email', [DataRequired(), Email(), user_authenticate],
        description='Email')
    password = PasswordField(
        'Password', [DataRequired(), pw_authenticate], description='Password')


class AddVehicleForm(FlaskForm):
    """ Form to add new vehicle. """
    name = StringField(
        'Vehicle Name', [DataRequired(), Length(1, 64)],
        description="Your Vehicle's Name")
    manufactured = DateField('Date Manufactured',
                             [DataRequired(), logical_date])
    current_mileage = IntegerField(
        'Current Mileage',
        [DataRequired(), NumberRange(1, 2000000)])
    standard_schedule = BooleanField('Add Standard Maintenance Schedule')


class EditVehicleForm(FlaskForm):
    """ Form to edit vehicle. """
    name = StringField(
        'Vehicle Name', [DataRequired(), Length(1, 64)],
        description="Your Vehicle's Name")
    manufactured = DateField('Date Manufactured',
                             [DataRequired(), logical_date])
    submit_edit = SubmitField('Edit Vehicle')

    # vehicle = Vehicle.query.filter(Vehicle.id == form.email.data).first()
    # vehicle.last_odometer()


class NewOdometerForm(FlaskForm):
    """ Form to add new Odometer readings """
    # Allows passing back of vehicle object for validation.
    vehicle = HiddenField()
    reading = IntegerField(
        'Current Mileage',
        [DataRequired(),
         NumberRange(1, 2000000), greater_odometer])
    submit_odometer = SubmitField('Add Mileage')

    


class NewMaintenanceForm(FlaskForm):
    """ Form to create a new maintenance task. """


class EditMaintenanceForm(FlaskForm):
    """ Form to allow editing of maintenance tasks. """


class NewLogForm(FlaskForm):
    """ Form to allow creation of new maintenance task logs. """
