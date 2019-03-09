""" Script to be run daily by Heroku Scheduler. This is used primarily for email
notifications. """
from auto_maint.scheduled_tasks import notify_users


def run():
    """ Functions to be run. """
    notify_users()

if __name__ == '__main__':
    run()
