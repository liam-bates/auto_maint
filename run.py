""" Run file to initiate gunicorn and background task. """
import os

from apscheduler.schedulers.background import BackgroundScheduler

from auto_maint.scheduled_tasks import notify_users


def run_web_script():
    # start the gunicorn server with custom configuration
    # You can also using app.run() if you want to use the flask built-in server -- be careful about the port
    os.system('gunicorn auto_maint:app')


def start_scheduler():

    # define a background schedule
    # Attention: you cannot use a blocking scheduler here as that will block the script from proceeding.
    scheduler = BackgroundScheduler()

    # add your job
    scheduler.add_job(func=notify_users, trigger="interval", minutes=5)

    # start the scheduler
    scheduler.start()


def run():
    start_scheduler()
    run_web_script()


if __name__ == '__main__':
    run()
