from email.message import EmailMessage

from flask import flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from auto_maint import app, db
from auto_maint.helpers import email, login_required
from auto_maint.models import Log, Maintenance, Odometer, User, Vehicle


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

                # Generate Email message to send
                msg = EmailMessage()
                msg['Subject'] = 'Welcome to Auto Maintenance!'
                msg['From'] = 'auto_maint@liam-bates.com'
                msg['To'] = user.email

                # Generate HTML for email
                html = render_template('email/welcome.html', user=user)
                msg.set_content(html, subtype='html')

                # Send email
                email(msg)

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
                flash('Unable to add mileage as it is lower than a previous '\
                    'reading.', 'danger')

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
            # Check the odometer values before and after from the database.
            odo_before = Odometer.query.filter(
                lookup_vehicle.vehicle_id == Odometer.vehicle_id).filter(
                    Odometer.reading_date < request.form['date']).order_by(
                        Odometer.reading_date.desc()).first()
            odo_after = Odometer.query.filter(
                lookup_vehicle.vehicle_id == Odometer.vehicle_id).filter(
                    Odometer.reading_date > request.form['date']).order_by(
                        Odometer.reading_date).first()

            mileage = int(request.form['mileage'])
            logical = True

            # Check mileage entered matches logic of existing odometer readings
            if odo_before:
                if odo_before.reading > mileage:
                    logical = False
            if odo_after:
                if odo_after.reading < mileage:
                    logical = False

            # If illogical flash error, otherwise add the new log with odometer
            if not logical:
                flash('Unable to create new log as listed mileage does not '\
                'correspond with existing odometer readings. Check odometer '\
                'readings.', 'danger')
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


@app.template_filter('age')
def age_format(value):
    """ Custom formatting for age, converting from days to years. """

    value = value / 365.2524

    return "{:,.2f} years".format(value)


@app.route("/odo/<reading_id>/delete", methods=['GET'])
@login_required
def delete_odometer(reading_id):
    """Takes a URL and deletes the odometer, by the ID provided"""

    # Query the db for a matching vehicle
    del_odom = Odometer.query.filter_by(reading_id=reading_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_odom.vehicle.user_id == session["user_id"]:
        # Test if it is the last odometer reading.
        if len(del_odom.vehicle.odo_readings) <= 1:
            flash('Cannot delete last odomter reading. Add another before '\
                'attempting to remove the last reading.', 'danger')
        else:
            del_odom.delete()
            flash(f'Odometer reading deleted.', 'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to odometer record.', 'primary')

    return redirect(f'/vehicle/{del_odom.vehicle.vehicle_id}')


@app.route("/maintenance/<maintenance_id>/delete", methods=['GET'])
@login_required
def delete_maintenance(maintenance_id):
    """Takes a URL and deletes the vehicle, by the ID provided"""

    # Query the db for a matching vehicle
    del_maintenance = Maintenance.query.filter_by(
        maintenance_id=maintenance_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_maintenance.vehicle.user_id == session["user_id"]:
        del_maintenance.delete()
        flash(f'{del_maintenance.name} maintenance task deleted.', 'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to maintenance record.', 'primary')

    return redirect(f'/vehicle/{del_maintenance.vehicle_id}')


@app.route("/log/<log_id>/delete", methods=['GET'])
@login_required
def delete_log(log_id):
    """Takes a URL and deletes the log entry, by the ID provided"""

    # Query the db for a matching vehicle
    del_log = Log.query.filter_by(log_id=log_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_log.maintenance.vehicle.user_id == session["user_id"]:
        del_log.delete()
        flash(f'Log entry deleted.', 'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to log entry.', 'danger')

    return redirect(
        f'/vehicle/{del_log.maintenance.vehicle_id}/maintenance/{del_log.maintenance_id}'
    )


@app.route("/vehicle/edit/<vehicle_id>", methods=['POST'])
@login_required
def edit_vehicle(vehicle_id):
    """ Allows for the editing of a vehicle's attributes using POST method. """
    # If a POST request check that all fields completed, otherwise flash error
    if request.form['vehicle_name'] == '' or request.form[
            'date_manufactured'] == '':
        flash(u'Missing required field/s when editing vehicle.', 'danger')
    else:
        # Pull vehicle from db using id
        ed_vehicle = Vehicle.query.filter(
            Vehicle.vehicle_id == vehicle_id).first()

        # Ensure requesting user owns the record
        if ed_vehicle.user_id == session["user_id"]:
            # Update fields.
            ed_vehicle.vehicle_name = request.form['vehicle_name']
            ed_vehicle.vehicle_built = request.form['date_manufactured']

            flash(u'Vehicle information updated.', 'primary')

            db.session.commit()

        return redirect(f'/vehicle/{vehicle_id}')


@app.route("/maintenance/edit/<maintenance_id>", methods=['POST'])
@login_required
def edit_maintenance(maintenance_id):
    """ Allows the editing of maintenance tasks via POST method. """
    # If a POST request check that all fields completed, otherwise flash error

    if any(field is '' for field in [
            request.form['name'], request.form['freq_miles'],
            request.form['freq_months']
    ]):
        flash(u'Missing required field/s when editing maintenance task.',
              'danger')
    else:
        # Pull vehicle from db using id
        ed_maintenance = Maintenance.query.filter(
            Maintenance.maintenance_id == maintenance_id).first()

        # Ensure requesting user owns the record
        if ed_maintenance.vehicle.user_id == session["user_id"]:
            # Update fields.
            ed_maintenance.name = request.form['name']
            ed_maintenance.description = request.form['description']
            ed_maintenance.freq_miles = request.form['freq_miles']
            ed_maintenance.freq_months = request.form['freq_months']

        flash(u'Maintenance information updated.', 'primary')

        db.session.commit()

        return redirect(
            f'/vehicle/{ed_maintenance.vehicle_id}/maintenance/{ed_maintenance.maintenance_id}'
        )
