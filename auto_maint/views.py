from email.message import EmailMessage

from flask import flash, jsonify, redirect, render_template, request, session
from werkzeug.security import generate_password_hash

from auto_maint import app, db
from auto_maint.forms import (AddVehicleForm, LoginForm, NewOdometerForm,
                              RegistrationForm, EditVehicleForm,
                              NewMaintenanceForm)
from auto_maint.helpers import email, login_required, standard_schedule
from auto_maint.models import Log, Maintenance, Odometer, User, Vehicle


@app.template_filter('mileage')
def mileage_format(value):
    """ Custom formatting for mileage. """
    return "{:,} miles".format(value)


@app.template_filter('age')
def age_format(value):
    """ Custom formatting for age, converting from days to years. """

    value = value / 365.2524

    return "{:,.2f} years".format(value)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Index view."""
    # Get the form data
    reg_form = RegistrationForm(request.form)
    login_form = LoginForm(request.form)

    # If login form validated move to home page
    if login_form.validate_on_submit():
        return redirect('/home')

    # Redirect to the home route if the user already logged in
    if session.get("user_id"):
        return redirect('/home')

    # Otherwise render the index page
    return render_template(
        'index.html', login_form=login_form, reg_form=reg_form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """ Takes the user registration form and creates a new user if
    validated. """

    # Get the form data
    form = RegistrationForm(request.form)
    # Check if form validated
    if form.validate_on_submit():
        # Create a new user object, with hashed password
        user = User(form.email.data,
                    generate_password_hash(form.password.data), form.name.data)
        # Flash thank you message
        flash('Account succesfully created.', 'success')

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

        # Confirm to browser that all okay
        return jsonify(status='ok')

    # Render index page again with errors
    return render_template('index.html', reg_form=form)


@app.route('/home', methods=['POST', 'GET'])
@login_required
def home():
    """ Home landing page for users. Showing a table of their vehicles. Also
    allows the creation of new vehicles via a modal form. """
    vehicle_form = AddVehicleForm(request.form)

    if vehicle_form.validate_on_submit():
        new_vehicle = Vehicle(session["user_id"], vehicle_form.name.data,
                              vehicle_form.manufactured.data)
        # Use method to add new odometer reading for the vehicle
        new_vehicle.add_odom_reading(vehicle_form.current_mileage.data)

        if vehicle_form.standard_schedule.data:
            standard_schedule(new_vehicle)

        flash(f'{new_vehicle.vehicle_name} added to your vehicle list.',
              'success')
        # Confirm to browser that all okay
        return jsonify(status='ok')
    # Query db for users info and vehicles
    vehicles = Vehicle.query.filter(
        Vehicle.user_id == session["user_id"]).all()
    user = User.query.filter(User.user_id == session["user_id"]).first()

    return render_template(
        "home.html", vehicles=vehicles, user=user, vehicle_form=vehicle_form)


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    """ Log user out. """

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
    """ Provides an overview of a vehicle record and allows posting of new
    odometer readings. """

    # Pull vehicle from db using id
    lookup_vehicle = Vehicle.query.filter(
        Vehicle.vehicle_id == vehicle_id).first()

    # Verify the user has access to the record and that it exists
    if not lookup_vehicle or lookup_vehicle.user_id != session['user_id']:
        flash(u'Unauthorized access to vehicle record.', 'danger')
        return redirect('/home')

    # Forms
    odometer_form = NewOdometerForm(request.form)
    edit_form = EditVehicleForm(request.form)
    maintenance_form = NewMaintenanceForm(request.form)

    # Send vehicle object back to the forms for validation
    odometer_form.vehicle.data = lookup_vehicle
    maintenance_form.vehicle.data = lookup_vehicle

    # Check if odometer click POST / validated
    if odometer_form.submit_odometer.data and odometer_form.validate_on_submit(
    ):
        # Add the reading
        lookup_vehicle.add_odom_reading(odometer_form.reading.data)
        flash(f'New mileage reading added.', 'success')

    # Check if edit click POST / validated
    elif edit_form.submit_edit.data and edit_form.validate_on_submit():
        # Update fields.
        lookup_vehicle.vehicle_name = edit_form.name.data
        lookup_vehicle.vehicle_built = edit_form.manufactured.data
        # Flash a confirmation message
        flash(u'Vehicle information updated.', 'success')
        # Commit to DB
        db.session.commit()
        return jsonify(status='ok')
    # Check if new maintenance form POST / validated
    elif maintenance_form.submit_maintenance.data and maintenance_form.validate_on_submit():
        # Create new maintenance task
        new_maintenance = Maintenance(lookup_vehicle.vehicle_id,
                                      maintenance_form.name.data,
                                      maintenance_form.description.data,
                                      maintenance_form.freq_miles.data,
                                      maintenance_form.freq_months.data)

        # Check if log data also given
        if maintenance_form.log_date.data and maintenance_form.log_miles.data:
            new_maintenance.add_log(maintenance_form.log_date.data,
                                    maintenance_form.log_miles.data,
                                    maintenance_form.log_notes.data)

        # Otherwise autogenerate one for the user
        else:
            new_maintenance.est_log()
        
        # Send confirmation to script
        return jsonify(status='ok')

    else:
        # Set existing values for the lookup form.
        edit_form.name.data = lookup_vehicle.vehicle_name
        edit_form.manufactured.data = lookup_vehicle.vehicle_built

    # Render vehicle template
    return render_template(
        'vehicle.html',
        vehicle=lookup_vehicle,
        user=lookup_vehicle.user,
        odometer_form=odometer_form,
        edit_form=edit_form,
        maintenance_form=maintenance_form)

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
        flash(u'Unauthorized access to vehicle record.', 'danger')
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
            flash('Cannot delete last odometer reading. Add another before '\
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
