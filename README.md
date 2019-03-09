# Auto Maintenance
Simple web app to remind me to perform maintenance tasks on my car.

## Summary

Auto Maintenance is a Flask web app that was created as my final CS50 project. The app serves the purpose of reminding the user via email to perform regular maintenance on their vehicle in accordance with a standard or custom vehicle maintenance schedule. While many newer vehicles have a similar inbuilt feature, this is not transparent and many older vehicles such as mine lack this feature.

The app utilizes Flask, SQLAlchemy, Postgres and SMTP to function, in addition to a number of other extensions. 

I personally host a working version of the app on a free Heroku dyno [here](http://auto-maint.liam-bates.com). Using Heroku Scheduler the app runs a notification script daily to ensure that users are reminded of required vehicle maintenace even if the app dyno is sleeping.
