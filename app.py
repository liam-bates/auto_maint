"""Web app to save maintenance schedule of a users car"""

from flask import Flask, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session

from models import User, db

app = Flask(__name__)

# Iniate DB / SQLAlchemy
app.config[
    "SQLALCHEMY_DATABASE_URI"] = "postgresql://liambates:test@localhost/auto"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initiate session tracking type
app.config["SESSION_TYPE"] = "sqlalchemy"
Session(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Index route"""
    # Check if a standard GET request
    if request.method == 'GET':
        # If so render the landing page
        return render_template('index.html')

    # Forget any user_id
    session.clear()

    # Query the DB for a matching email address and save it as user object
    user = User.query.filter(User.email == request.form['email']).first()

    # Check if user is blocked
    if user.blocked:
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
        session["user_id"] = user.id
        # Reset failed login attempts
        user.failed_logins = 0
        # Commit to DB
        db.session.commit()
        return f"Logged in succesfully. Welcome {user.name}!"


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
