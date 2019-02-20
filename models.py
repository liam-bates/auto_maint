"""Python models defined"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define an object of a user within the context of the DB
class User(db.Model):
    """Users of the website"""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(93), nullable=False)
    name = db.Column(db.String (128), nullable=False)
    failed_logins = db.Column(
        db.SmallInteger, default=0, nullable=False)
    blocked = db.Column(db.Boolean, default =False)
    
