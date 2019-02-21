"""Web app to save maintenance schedule of a users car"""

from functools import wraps
from flask import Flask, redirect, render_template, request, session
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
    # Check if a standard GET request
    if request.method == 'GET':
        # If user already signed in redirect to the cars route
        if session.get("user_id"):
            return redirect('/cars')

        # If so render the landing page
        return render_template('index.html')

    # Ensure user provided email and password on form
    if not request.form['email'] or not request.form['password']:
        return "Error: No username and/or password."

    # Query the DB for a matching email address and save it as user object
    user = User.query.filter(User.email == request.form['email']).first()

    # Check if user is blocked
    if user and user.blocked:
        return "ERROR: User Blocked"

    # Check that a user was found and password correct
    if not user or not check_password_hash(user.password_hash,
                                           request.form['password']):
        # If failed check if username exists
        if user and user.failed_logins == 4:
            # Block the user if this is their
            user.blocked = True
        # Else if failed_logins less than 4 increment
        elif user and user.failed_logins < 4:
            user.failed_logins += 1
        # Commit to DB
        db.session.commit()
        # Return error
        return "invalid username and/or password"
    else:
        # Save user id as session user id
        session["user_id"] = user.user_id
        # Reset failed login attempts
        user.failed_logins = 0
        # Commit to DB
        db.session.commit()
        return redirect('/cars')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page route"""
    # Check if a standard request and render registration page if so
    if request.method == 'GET':
        return render_template('register.html')

    # Ensure the user has submitted all of the required fields
    if not request.form['email']:
        return "ERROR: No email address provided"
    if not request.form['name']:
        return "ERROR: No name provided"
    if not request.form['password']:
        return "ERROR: No password provided"
    if not request.form['confirm']:
        return "ERROR: No password confirmation provided"

    # Check that password and password match
    if request.form['password'] != request.form['confirm']:
        return "ERROR: Password and password confirmation do not match"

    # Ensure no other registered users have that email
    if User.query.filter(User.email == request.form['email']).count():
        return "ERROR: Email already registered"

    # Create a new User object with a hashed password
    user = User(
        email=request.form['email'],
        name=request.form['name'],
        password_hash=generate_password_hash(request.form['password']))

    # Add to DB session
    db.session.add(user)
    # Commit to the DB
    db.session.commit()

    # Obtain new user model from the db
    user = User.query.filter(User.email == request.form['email']).first()

    # Start new session
    session["user_id"] = user.user_id
    db.session.commit()

    return redirect('/cars')


@app.route('/cars', methods=['GET', 'POST'])
@login_required
def cars():

    # Query db for users info and cars
    # TODO: Add method for the user to pull in all of their cars
    cars = Car.query.filter(Car.user_id == session["user_id"]).all()
    user = User.query.filter(User.user_id == session["user_id"]).first()

    return render_template("cars.html", cars=cars, user=user)


@app.route('/addcar', methods=['GET', 'POST'])
@login_required
def add_car():

    # If a GET request send back form page
    if request.method == 'GET':
        return render_template("add_car.html")

    # If a POST request check that all fields completed
    if None in (request.form['car_name'], request.form['date_manufactured'],
                request.form['mileage']):
        return "ERROR: Missing required field/s on form."

    # Create a new car object and add to db using add method
    new_car = Car(
        user_id=session["user_id"],
        car_name=request.form['car_name'],
        car_built=request.form['date_manufactured']).add()

    # Use method to add new odometer reading for the car
    new_car.add_odom_reading(request.form['mileage'])

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
        return redirect('/cars')

    return "ERROR: Attempting to delete unauthorized record"


@app.route("/car/<car_id>", methods=['GET'])
@login_required
def car(car_id):
    """Provides an overview of a car record. Allows editing and deletion."""

    # Pull car from db using id
    car = Car.query.filter(Car.car_id == car_id).first()

    # Verify the user has access to the record and that it exists
    if not car or car.user_id != session['user_id']:
        return "ERROR: Unauthorized access"
    
    # Render car template
    return render_template('car.html', car=car)
