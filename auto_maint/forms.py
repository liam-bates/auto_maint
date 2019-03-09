""" Forms used throughout the web app, using WTForms. """
from datetime import date

from flask import flash
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash
from wtforms import (BooleanField, HiddenField, PasswordField, StringField,
                     SubmitField, TextAreaField, ValidationError)
from wtforms.fields.html5 import DateField, IntegerField
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                NumberRange, Optional)

from auto_maint.models import Odometer, User


def available(form, field):
    """ Check if the user's email address has not already been registered on the
    web app. """
    # Ensure no other registered users have that email
    if User.query.filter(User.email == field.data).count():
        raise ValidationError('Email already registered.')


def user_authenticate(form, field):
    """ Ensure user exists, is not blocked and that the provided password was
    correct. """
    # Query the DB for a matching email address and save it as user object
    user = User.query.filter(User.email == field.data).first()

    # Check if user exists
    if not user:
        raise ValidationError('Unknown Email provided.')


def pw_authenticate(form, field):
    """ Authenticate the user's password by checking the stored hash. """
    user = User.query.filter(User.email == form.email.data).first()
    # Check if User known
    if user:
        # Check if blocked
        if user.blocked:
            user.failed_login()
            raise ValidationError()

        elif not user.email_confirmed:
            # Send the user another welcome / verification email
            user.verification_email()

            flash(
                """Email not yet confirmed. Please use the
            verification link in the email provided. An additional email 
            with verification link has been sent to you.""", 'danger')

        # Check if correct password
        elif not check_password_hash(user.password_hash, field.data):
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
    # Ensure that new mileage is higher than previous
    if field.data < form.vehicle.data.last_odometer().reading:
        raise ValidationError(
            'New mileage reading must be higher than a previous reading.')


def logical_log_mileage(form, field):
    """ Ensure that log mileage is logical when compared with existing odometer
    readings. """
    # Check the odometer values before and after from the database.
    odo_before = Odometer.query.filter(
        form.vehicle.data.vehicle_id == Odometer.vehicle_id).filter(
            Odometer.reading_date < form.log_date.data).order_by(
                Odometer.reading_date.desc()).first()
    odo_after = Odometer.query.filter(
        form.vehicle.data.vehicle_id == Odometer.vehicle_id).filter(
            Odometer.reading_date > form.log_date.data).order_by(
                Odometer.reading_date).first()

    logical = True

    # Check mileage entered matches logic of existing odometer readings
    if odo_before:
        if odo_before.reading > field.data:
            logical = False
    if odo_after:
        if odo_after.reading < field.data:
            logical = False

    # If illogical flash error, otherwise add the new log with odometer
    if not logical:
        raise ValidationError("""Unable to create new log as listed mileage
            does not correspond with existing odometer readings. Check odometer
            readings to ensure they are correct.""")


class RequiredIf(DataRequired):
    """ Validator which makes a field required if another field is set and has a
    truthy value. """

    field_flags = ('requiredif', )

    def __init__(self, other_field_name, message=None, *args, **kwargs):
        self.other_field_name = other_field_name
        self.message = message

    def __call__(self, form, field):
        other_field = form[self.other_field_name]
        if other_field is None:
            raise Exception(
                'You must also complete "%s" on form' % self.other_field_name)
        if bool(other_field.data):
            super(RequiredIf, self).__call__(form, field)
        else:
            Optional().__call__(form, field)


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
    submit_registration = SubmitField('Register')


class LoginForm(FlaskForm):
    """ Form to login app users. """
    email = StringField(
        'Email', [DataRequired(), Email(), user_authenticate],
        description='Email')
    password = PasswordField(
        'Password', [DataRequired(), pw_authenticate], description='Password')
    submit_login = SubmitField('Login')


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
    vehicle = HiddenField()
    name = StringField(
        'Maintenance Task Name',
        [DataRequired(), Length(1, 64)],
        description="Maintenance Task Name")
    description = TextAreaField(
        'Task Description (optional)',
        [Optional(), Length(max=256)],
        description="Task Description")
    freq_miles = IntegerField(
        'Frequency (miles)',
        [DataRequired(), NumberRange(1, 1000000)])
    freq_months = IntegerField(
        'Frequency (months)',
        [DataRequired(), NumberRange(1, 240)])
    log_date = DateField('Date', [RequiredIf('log_miles'), logical_date])
    log_miles = IntegerField(
        'Mileage',
        [NumberRange(1, 2000000),
         RequiredIf('log_date'), logical_log_mileage])
    log_notes = TextAreaField(
        'Notes', [Optional(), Length(max=256)], description="Notes")
    submit_maintenance = SubmitField('Add Maintenance Task')


class EditMaintenanceForm(FlaskForm):
    """ Form to allow editing of maintenance tasks. """
    name = StringField(
        'Maintenance Task Name',
        [DataRequired(), Length(1, 64)],
        description="Maintenance Task Name")
    description = TextAreaField(
        'Task Description (optional)',
        [Optional(), Length(max=256)],
        description="Task Description")
    freq_miles = IntegerField(
        'Frequency (miles)',
        [DataRequired(), NumberRange(1, 1000000)])
    freq_months = IntegerField(
        'Frequency (months)',
        [DataRequired(), NumberRange(1, 240)])
    submit_edit = SubmitField('Edit Maintenance Task')


class NewLogForm(FlaskForm):
    """ Form to allow creation of new maintenance task logs. """
    vehicle = HiddenField()
    log_date = DateField('Date', [DataRequired(), logical_date])
    log_miles = IntegerField(
        'Mileage',
        [DataRequired(),
         NumberRange(1, 2000000), logical_log_mileage])
    log_notes = TextAreaField(
        'Notes', [Optional(), Length(max=256)], description="Notes")
    submit_log = SubmitField('Add Log')


class UpdateName(FlaskForm):
    name = StringField(
        'Name',
        validators=[DataRequired(), Length(2, 64)],
        description='Your Name')
    submit_name = SubmitField('Update Name')


class UpdateEmail(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(),
                    Email(),
                    Length(5, 256), available],
        description='Your Email')
    submit_email = SubmitField('Update Email')


class UpdatePassword(FlaskForm):
    email = HiddenField()
    current_password = PasswordField(
        'Current Password', [DataRequired(), pw_authenticate],
        description='Current Password')
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(6, 64),
            EqualTo('confirm', 'New password and confirmation do not match.')
        ],
        description='New Password')
    confirm = PasswordField(
        validators=[DataRequired()], description='Confirm New Password')
    submit_password = SubmitField('Update Password')


class ForgotPassword(FlaskForm):
    email = StringField(
        'Email', [DataRequired(), Email(), user_authenticate],
        description='Email')
    submit_forgot = SubmitField('Send Reset Email')


class ResetPassword(FlaskForm):
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(6, 64),
            EqualTo('confirm', 'New password and confirmation do not match.')
        ],
        description='New Password')
    confirm = PasswordField(
        validators=[DataRequired()], description='Confirm New Password')
    submit_password = SubmitField('Update Password')
