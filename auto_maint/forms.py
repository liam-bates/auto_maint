from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, ValidationError
from wtforms.validators import DataRequired, EqualTo, Length, Email

from auto_maint.models import User


def available(form, field):
    # Ensure no other registered users have that email
    if User.query.filter(User.email == field.data).count():
        raise ValidationError('Email already registered.')


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
