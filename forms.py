from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from email_validator import validate_email, EmailNotValidError
import re
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('I am a:', choices=[('patient', 'Patient'), ('doctor', 'Doctor')], validators=[DataRequired()])
    patient_id = StringField('Patient ID', validators=[Length(max=20)])
    doctor_id = StringField('Doctor ID', validators=[Length(max=20)])
    medical_credentials = StringField('Medical Credentials', validators=[Length(max=120)])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        try:
            v = validate_email(email.data)
            email.data = v["email"]
        except EmailNotValidError as e:
            raise ValidationError(str(e))

        user = User.query.filter_by(email(email.data)).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

    def validate_password(self, password):
        password_data = password.data
        if len(password_data) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        if not re.search(r'\d', password_data):
            raise ValidationError('Password must contain at least one number.')

    def validate_patient_id(self, patient_id):
        if self.user_type.data == 'patient':
            if not patient_id.data.isdigit() or len(patient_id.data) <= 5 or patient_id.data == '0' * len(patient_id.data):
                raise ValidationError('Patient ID must be numeric, longer than 5 digits, and not a stream of zeros.')
            user = User.query.filter_by(patient_id=patient_id.data).first()
            if user:
                raise ValidationError('Patient ID is already in use. Please choose a different one.')

    def validate_doctor_id(self, doctor_id):
        if self.user_type.data == 'doctor':
            if not doctor_id.data.isdigit() or len(doctor_id.data) <= 5 or doctor_id.data == '0' * len(doctor_id.data):
                raise ValidationError('Doctor ID must be numeric, longer than 5 digits, and not a stream of zeros.')
            user = User.query.filter_by(doctor_id(doctor_id.data)).first()
            if user:
                raise ValidationError('Doctor ID is already in use. Please choose a different one.')

    def validate_medical_credentials(self, medical_credentials):
        if self.user_type.data == 'doctor' and not medical_credentials.data:
            raise ValidationError('Medical credentials are required for doctors.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
