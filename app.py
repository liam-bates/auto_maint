"""Web app to save maintenance schedule of a users car"""

from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from models import Car, Odometer, User, db

app = Flask(__name__)

# Iniate DB / SQLAlchemy
app.config[
    "SQLALCHEMY_DATABASE_URI"] = "postgresql://liambates:test@localhost/auto"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initiate session tracking type
app.config["SESSION_TYPE"] = "sqlalchemy"
Session(app)


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


@app.route('/', methods=['GET', 'POST'])
def index():
    """Index route"""
    # If a GET request
    if request.method == 'GET':
        # Redirect to the home route if the user already logged in
        if session.get("user_id"):
            return redirect('/cars')

        # Render the landing page
        return render_template('index.html')

    # If a POST request ensure user provided email and password on form
    if not request.form['email'] or not request.form['password']:
        flash(u'No username and/or password provided', 'danger')

    else:
        # Query the DB for a matching email address and save it as user object
        user = User.query.filter(User.email == request.form['email']).first()

        # Check if user
        if not user:
            flash(u'Incorrect username and/or password provided', 'danger')
        else:
            # If user is blocked flash a message to warn them
            if user.blocked:
                flash(u'Account Blocked', 'danger')
            else:
                # Check that password correct
                if not check_password_hash(user.password_hash,
                                           request.form['password']):
                    # Record failed attempt
                    user.failed_logins += 1
                    # Block the user if this is their 5th attempt
                    if user and user.failed_logins >= 5:
                        user.blocked = True
                    # Commit to DB
                    db.session.commit()
                    # Return error
                    flash(u'Incorrect username and/or password provided',
                          'danger')
                # Correct password provided
                else:
                    # Save user id as session user id
                    session["user_id"] = user.user_id
                    # Reset failed login attempts
                    user.failed_logins = 0
                    # Commit to DB
                    db.session.commit()
                    # Direct to home landing page
                    return redirect('/cars')

    # Return index page again
    return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """ Registration page to allow users to create an account on the app. """

    # Check if a GET request and render registration page if so
    if request.method == 'GET':
        return render_template('register.html')

    # Otherwise treat as POST and ensure user has submitted all required fields
    if any(field is '' for field in [
            request.form['email'], request.form['name'],
            request.form['password'], request.form['confirm']
    ]):
        flash(u'Missing required field/s for new user account', 'danger')

    else:
        # Check that password and password match
        if request.form['password'] != request.form['confirm']:
            flash(u'Password and password confirmation do not match', 'danger')
        else:
            # Ensure no other registered users have that email
            if User.query.filter(User.email == request.form['email']).count():
                flash(u'Email already registered ', 'danger')
            else:
                # Create a new User object with a hashed password
                user = User(
                    email=request.form['email'],
                    name=request.form['name'],
                    password_hash=generate_password_hash(
                        request.form['password']))

                # Add to DB session
                db.session.add(user)
                # Commit to the DB
                db.session.commit()

                # Obtain new user model from the db
                user = User.query.filter(
                    User.email == request.form['email']).first()

                # Start a new user session
                session["user_id"] = user.user_id
                db.session.commit()

                # Redirect to the vehicle landing page
                return redirect('/cars')

    return redirect('/register')


@app.route('/cars', methods=['GET', 'POST'])
@login_required
def cars():
    """ Home landing page for users. Showing a table of their vehicles """

    # Query db for users info and cars
    cars = Car.query.filter(Car.user_id == session["user_id"]).all()
    user = User.query.filter(User.user_id == session["user_id"]).first()

    return render_template("cars.html", cars=cars, user=user)


@app.route('/addcar', methods=['GET', 'POST'])
@login_required
def add_car():
    """ Simple page to allow user to create a new vehicle in the app. """

    # If a GET request send back form page
    if request.method == 'GET':
        return render_template("add_car.html")

    # If a POST request check that all fields completed, otherwise flash error
    if any(field is '' for field in [
            request.form['car_name'], request.form['date_manufactured'],
            request.form['mileage']
    ]):
        flash(u'Missing required field/s when adding new vehicle.', 'danger')
    else:
        # Create a new car object and add to db using add method
        new_car = Car(
            user_id=session["user_id"],
            car_name=request.form['car_name'],
            car_built=request.form['date_manufactured']).add()

        # Use method to add new odometer reading for the car
        new_car.add_odom_reading(request.form['mileage'])
        flash(f'{new_car.car_name} added to your vehicle list.', 'primary')
    # Return to the landing screen
    return redirect('/cars')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to landing page
    return redirect("/")


@app.route("/car/<car_id>/delete", methods=['GET'])
@login_required
def delete_car(car_id):
    """Takes a URL and deletes the car, by the ID provided"""

    delete_car = Car.query.filter_by(car_id=car_id).first()

    if delete_car.user_id == session["user_id"]:
        delete_car.delete()
        flash(f'{delete_car.car_name} deleted from your vehicle list.',
              'primary')
    else:
        flash('Unauthorized access to vehicle record.', 'primary')

    return redirect('/cars')


@app.route("/car/<car_id>", methods=['GET'])
@login_required
def car(car_id):
    """Provides an overview of a car record. Allows editing and deletion."""

    # Pull car from db using id
    car = Car.query.filter(Car.car_id == car_id).first()

    # Verify the user has access to the record and that it exists
    if not car or car.user_id != session['user_id']:
        flash(u'Unauthorized access to vehicle record', 'danger')
        return redirect('/cars')

    # Render car template
    return render_template('car.html', car=car)
