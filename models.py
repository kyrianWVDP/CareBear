from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    user_type = db.Column(db.String(10), nullable=False)
    patient_id = db.Column(db.String(20), unique=True, nullable=True)
    doctor_id = db.Column(db.String(20), unique=True, nullable=True)
    medical_credentials = db.Column(db.String(120), nullable=True)
    measurements = db.relationship('Measurement', backref='user', lazy=True)
    alarms = db.relationship('Alarm', backref='user', lazy=True)

class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    heart_rate = db.Column(db.Integer, nullable=False)
    spo2 = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Alarm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time = db.Column(db.String(5), nullable=False)  # Format HH:MM
    label = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
