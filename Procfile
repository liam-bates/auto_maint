web: gunicorn app:app --preload
release: export FLASK_APP=auto_maint
release: flask db upgrade