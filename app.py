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
        # If user already signed in redirect to the home route
        if session.get("user_id"):
            return redirect('/home')
        
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
        return home()


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
    return f"Thanks for registering {user.name}!"


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():


    # newcar = Odometer(car_id=3, reading=102000, reading_date=datetime.date(2019, 2, 1))
    # db.session.add(newcar)
    # db.session.commit()
    # print()

    cars = Car.query.filter(Car.user_id == session["user_id"]).all()

    return render_template("home.html", cars=cars)




@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to landing page
    return redirect("/")
