"""Web app to save maintenance schedule of a users vehicle"""

from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from models import Vehicle, User, Maintenance, db

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
            return redirect('/home')

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
                    return redirect('/home')

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
                return redirect('/home')

    return redirect('/register')


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    """ Home landing page for users. Showing a table of their vehicles """

    # Query db for users info and vehicles
    vehicles = Vehicle.query.filter(
        Vehicle.user_id == session["user_id"]).all()
    user = User.query.filter(User.user_id == session["user_id"]).first()

    return render_template("home.html", vehicles=vehicles, user=user)


@app.route('/addvehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    """ Simple page to allow user to create a new vehicle in the app. """

    # If a GET request send back form page
    if request.method == 'GET':
        # Query DB for user
        user = User.query.filter(User.user_id == session["user_id"]).first()
        return render_template("add_vehicle.html", user=user)

    # If a POST request check that all fields completed, otherwise flash error
    if any(field is '' for field in [
            request.form['vehicle_name'], request.form['date_manufactured'],
            request.form['mileage']
    ]):
        flash(u'Missing required field/s when adding new vehicle.', 'danger')
    else:
        # Create a new vehicle object and add to db using add method
        new_vehicle = Vehicle(
            user_id=session["user_id"],
            vehicle_name=request.form['vehicle_name'],
            vehicle_built=request.form['date_manufactured']).add()

        # Use method to add new odometer reading for the vehicle
        new_vehicle.add_odom_reading(request.form['mileage'])
        flash(f'{new_vehicle.vehicle_name} added to your vehicle list.',
              'primary')
    # Return to the landing screen
    return redirect('/home')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to landing page
    return redirect("/")


@app.route("/vehicle/<vehicle_id>/delete", methods=['GET'])
@login_required
def delete_vehicle(vehicle_id):
    """Takes a URL and deletes the vehicle, by the ID provided"""

    # Query the db for a matching vehicle
    del_vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_vehicle.user_id == session["user_id"]:
        del_vehicle.delete()
        flash(f'{del_vehicle.vehicle_name} deleted from your vehicle list.',
              'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to vehicle record.', 'primary')

    return redirect('/home')


@app.route("/vehicle/<vehicle_id>", methods=['GET', 'POST'])
@login_required
def vehicle(vehicle_id):
    """Provides an overview of a vehicle record. Allows editing and deletion."""

    # Pull vehicle from db using id
    lookup_vehicle = Vehicle.query.filter(
        Vehicle.vehicle_id == vehicle_id).first()

    # Verify the user has access to the record and that it exists
    if not lookup_vehicle or lookup_vehicle.user_id != session['user_id']:
        flash(u'Unauthorized access to vehicle record', 'danger')
        return redirect('/home')

    # Check is a POST has been made from odometer form
    if request.method == 'POST':
        # Ensure value given
        if not request.form['mileage']:
            flash(f'No mileage reading provided.', 'danger')
        else:
            mileage = int(request.form['mileage'])
            # Ensure that new mileage is higher than previous
            if mileage > lookup_vehicle.last_odometer().reading:
                lookup_vehicle.add_odom_reading(mileage)
                flash(f'Mileage reading added.', 'primary')
            # Otherwise return an error
            else:
                flash(
                    f'Unable to add mileage as it is lower than a previous reading.',
                    'danger')

    # Query DB for user's info
    user = User.query.filter(User.user_id == session["user_id"]).first()
    # Render vehicle template
    return render_template('vehicle.html', vehicle=lookup_vehicle, user=user)


@app.route("/vehicle/<vehicle_id>/addmaint", methods=['GET', 'POST'])
@login_required
def add_maint(vehicle_id):
    """Allow user to add a maintenance schedule event."""

    # Pull vehicle from db using id
    lookup_vehicle = Vehicle.query.filter(
        Vehicle.vehicle_id == vehicle_id).first()

    # Check that user has access to this vehicle
    if not lookup_vehicle or lookup_vehicle.user_id != session['user_id']:
        flash(u'Unauthorized access to vehicle record', 'danger')
        return redirect('/home')

    # If a GET request send back form page
    if request.method == 'GET':
        # Query DB for user
        user = User.query.filter(User.user_id == session["user_id"]).first()
        return render_template("add_maint.html", user=user)

    # POST begins
    # Add the maintenance event for the vehicle.
    new_maintenance = lookup_vehicle.add_maintenance(
        request.form['name'], request.form['description'],
        request.form['freq_miles'], request.form['freq_months'])

    if any(
            field is not '' for field in
        [request.form['date'], request.form['mileage'], request.form['notes']
         ]):
        new_maintenance.add_log(request.form['date'], request.form['mileage'],
                                request.form['notes'])

    else:
        new_maintenance.est_log()

    flash(f'{request.form["name"]} maintenance record added', 'primary')
    return redirect("vehicle/" + vehicle_id)


@app.route(
    "/vehicle/<vehicle_id>/maintenance/<maintenance_id>",
    methods=['GET', 'POST'])
@login_required
def maintenance(vehicle_id, maintenance_id):
    """ Shows a details of a particular scheduled maintenance event and allows
    the user to create log entries for that task when performed. """
    # Pull vehicle, maintenance and user reocrds from db using id
    lookup_vehicle = Vehicle.query.filter(
        Vehicle.vehicle_id == vehicle_id).first()
    lookup_maintenance = Maintenance.query.filter(
        Maintenance.maintenance_id == maintenance_id).first()
    user = User.query.filter(User.user_id == session["user_id"]).first()

    # Verify the user has access to the record and that it exists
    if not lookup_vehicle.maintenance or lookup_vehicle.user_id != session[
            'user_id']:
        flash(u'Unauthorized access to vehicle record', 'danger')
        return redirect('/home')

    if request.method == 'POST':
        if request.form['date'] == '' or request.form['mileage'] == '':
            flash(u'Missing required field/s for new log entry', 'danger')
        else:
            lookup_maintenance.add_log(request.form['date'],
                                       request.form['mileage'],
                                       request.form['notes'])
            flash(u'New log entry added.', 'primary')

    return render_template(
        "maintenance.html", maintenance=lookup_maintenance, user=user)

@app.template_filter('mileage')
def mileage_format(value):
    """ Custom formatting for mileage. """
    return "{:,} miles".format(value)