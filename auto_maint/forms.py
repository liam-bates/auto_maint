from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash
from wtforms import PasswordField, StringField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length

from auto_maint.models import User


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
        'Email', [DataRequired(), Email(), user_authenticate], description='Email')
    password = PasswordField('Password', [DataRequired(), pw_authenticate], description='Password')
