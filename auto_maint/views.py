""" Auto Maintenance views. Also features GET routes for the deletion of
objects. """
from email.message import EmailMessage

from flask import flash, jsonify, redirect, render_template, request, session
from werkzeug.security import generate_password_hash

from auto_maint import app, db
from auto_maint.forms import (
    AddVehicleForm, EditMaintenanceForm, EditVehicleForm, LoginForm,
    NewLogForm, NewMaintenanceForm, NewOdometerForm, RegistrationForm,
    UpdateEmail, UpdateName, UpdatePassword)
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
    registration_form = RegistrationForm(request.form)
    login_form = LoginForm(request.form)

    # If login form validated move to home page
    if login_form.submit_login.data and login_form.validate_on_submit():
        return redirect('/home')

    # Check if form validated
    if (registration_form.submit_registration.data
            and registration_form.validate_on_submit()):
        # Create a new user object, with hashed password
        user = User(registration_form.email.data,
                    generate_password_hash(registration_form.password.data),
                    registration_form.name.data)
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

    # Redirect to the home route if the user already logged in
    if session.get("user_id"):
        return redirect('/home')

    # Otherwise render the index page
    return render_template(
        'index.html', login_form=login_form, reg_form=registration_form)


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
    elif (maintenance_form.submit_maintenance.data
          and maintenance_form.validate_on_submit()):
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


@app.route("/vehicle/<vehicle_id>/delete", methods=['GET'])
@login_required
def delete_vehicle(vehicle_id):
    """ Takes a URL and deletes the vehicle, by the ID provided. """

    # Query the db for a matching vehicle
    del_vehicle = Vehicle.query.filter_by(vehicle_id=vehicle_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_vehicle.user_id == session["user_id"]:
        del_vehicle.delete()
        flash(f'{del_vehicle.vehicle_name} deleted from your vehicle list.',
              'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to vehicle record.', 'danger')

    return redirect('/home')


@app.route("/odo/<reading_id>/delete", methods=['GET'])
@login_required
def delete_odometer(reading_id):
    """ Takes a URL and deletes the odometer, by the ID provided. """

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
        flash('Unauthorized access to odometer record.', 'danger')

    return redirect(f'/vehicle/{del_odom.vehicle.vehicle_id}')


@app.route("/maintenance/<maintenance_id>", methods=['GET', 'POST'])
@login_required
def maintenance(maintenance_id):
    """ Shows a details of a particular scheduled maintenance event and allows
    the user to create log entries for that task when performed. """
    # Pull vehicle, maintenance and user reocrds from db using id
    lookup_maintenance = Maintenance.query.filter(
        Maintenance.maintenance_id == maintenance_id).first()

    edit_form = EditMaintenanceForm(request.form)
    log_form = NewLogForm(request.form)

    log_form.vehicle.data = lookup_maintenance.vehicle

    # Verify the user has access to the record and that it exists
    if not lookup_maintenance or lookup_maintenance.vehicle.user_id != session[
            'user_id']:
        flash(u'Unauthorized access to vehicle record.', 'danger')
        return redirect('/home')

    if log_form.submit_log.data and log_form.validate_on_submit():
        lookup_maintenance.add_log(log_form.log_date.data,
                                   log_form.log_miles.data,
                                   log_form.log_notes.data)

        flash(u'New log entry added.', 'success')

        return jsonify(status='ok')

    if edit_form.submit_edit.data and edit_form.validate_on_submit():
        # Update fields.
        lookup_maintenance.name = edit_form.name.data
        lookup_maintenance.description = edit_form.description.data
        lookup_maintenance.freq_miles = edit_form.freq_miles.data
        lookup_maintenance.freq_months = edit_form.freq_months.data

        flash(u'Maintenance information updated.', 'success')

        db.session.commit()

        return jsonify(status='ok')

    # Set existing values for the edit form.
    edit_form.name.data = lookup_maintenance.name
    edit_form.description.data = lookup_maintenance.description
    edit_form.freq_miles.data = lookup_maintenance.freq_miles
    edit_form.freq_months.data = lookup_maintenance.freq_months

    return render_template(
        "maintenance.html",
        maintenance=lookup_maintenance,
        user=lookup_maintenance.vehicle.user,
        edit_form=edit_form,
        log_form=log_form)


@app.route("/maintenance/<maintenance_id>/delete", methods=['GET'])
@login_required
def delete_maintenance(maintenance_id):
    """ Takes a URL and deletes the vehicle, by the ID provided. """

    # Query the db for a matching vehicle
    del_maintenance = Maintenance.query.filter_by(
        maintenance_id=maintenance_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_maintenance.vehicle.user_id == session["user_id"]:
        del_maintenance.delete()
        flash(f'{del_maintenance.name} maintenance task deleted.', 'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to maintenance record.', 'danger')

    return redirect(f'/vehicle/{del_maintenance.vehicle_id}')


@app.route("/log/<log_id>/delete", methods=['GET'])
@login_required
def delete_log(log_id):
    """ Takes a URL and deletes the log entry, by the ID provided. """

    # Query the db for a matching vehicle
    del_log = Log.query.filter_by(log_id=log_id).first()

    # Test whatever was returned to see if the vehicle is owned by the user
    if del_log.maintenance.vehicle.user_id == session["user_id"]:
        del_log.delete()
        flash(f'Log entry deleted.', 'primary')
    # If not flash an error
    else:
        flash('Unauthorized access to log entry.', 'danger')

    return redirect(f'/maintenance/{del_log.maintenance_id}')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """ Settings page view, with POST method for editing attributes. """

    # Query DB for user data
    user = User.query.filter(User.user_id == session["user_id"]).first()
     
    # Define forms
    update_name = UpdateName(request.form)
    update_email = UpdateEmail(request.form)
    update_password = UpdatePassword(request.form)

    # Provide email address for update password form validation
    update_password.email.data = user.email

    # Check if update name form submitted / validated
    if update_name.submit_name.data and update_name.validate_on_submit():

        # Update name on DB and confirm success
        user.name = update_name.name.data
        db.session.commit()
        flash('Name updated.', 'success')

    # Check if update email form submitted / validated
    elif update_email.submit_email.data and update_email.validate_on_submit():
        
        # Update email on DB and confirm success
        user.email = update_email.email.data
        db.session.commit()
        flash('Email address updated.', 'success')

    # Check if update password form submitted / validated
    elif (update_password.submit_password.data
          and update_password.validate_on_submit()):

        # Update password hash on DB and confirm success
        user.password_hash = generate_password_hash(
            update_password.password.data)
        db.session.commit()
        flash('Password succesfully updated.', 'success')
    
    elif user.blocked:
        return logout()

    else:
        # Send current values to the form
        update_name.name.data = user.name
        update_email.email.data = user.email

    return render_template(
        'settings.html',
        user=user,
        update_name=update_name,
        update_email=update_email,
        update_password=update_password)

@app.route('/delete', methods=['GET'])
@login_required
def delete():
    """ Delete current user. """
    user = User.query.filter(User.user_id == session["user_id"]).first()
    user.delete()
    flash('Account deleted.', 'primary')
    return redirect('/')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    """ Log user out. """

    # Forget any user_id
    session.clear()

    # Redirect user to landing page
    return redirect("/")
