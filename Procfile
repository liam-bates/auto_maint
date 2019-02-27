web: gunicorn app:app
release: flask db migrate -m "Initial Deployment"
release: flask db upgrade