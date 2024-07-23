from flask import Flask, render_template, url_for, flash, redirect, request, jsonify
from config import Config
from extensions import db, bcrypt, login_manager
from forms import RegistrationForm, LoginForm
from models import User, Measurement, Alarm
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
import threading
import time
import pygame

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'your_secret_key'

db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)

# Initialize pygame mixer for sound
pygame.mixer.init()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = None

        def is_valid_id(id):
            # Check if ID is numeric, longer than 5 digits, and not a stream of 0s
            return id.isdigit() and len(id) > 5 and id != '0' * len(id)

        if form.user_type.data == 'patient':
            if not is_valid_id(form.patient_id.data):
                flash('Invalid Patient ID. It must be numeric, longer than 5 digits, and not a stream of zeros.', 'danger')
                return redirect(url_for('register'))
            user = User.query.filter_by(patient_id=form.patient_id.data).first()
            if user:
                flash('Patient ID is already in use. Please use a different ID.', 'danger')
                return redirect(url_for('register'))
        elif form.user_type.data == 'doctor':
            if not is_valid_id(form.doctor_id.data):
                flash('Invalid Doctor ID. It must be numeric, longer than 5 digits, and not a stream of zeros.', 'danger')
                return redirect(url_for('register'))
            user = User.query.filter_by(doctor_id=form.doctor_id.data).first()
            if user:
                flash('Doctor ID is already in use. Please use a different ID.', 'danger')
                return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, user_type=form.user_type.data)
        if form.user_type.data == 'patient':
            user.patient_id = form.patient_id.data
        elif form.user_type.data == 'doctor':
            user.doctor_id = form.doctor_id.data
            user.medical_credentials = form.medical_credentials.data
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'doctor':
        patients = User.query.filter_by(user_type='patient').all()
        return render_template('dashboard_doctor.html', patients=patients)
    else:
        measurements = Measurement.query.filter_by(user_id=current_user.id).order_by(Measurement.timestamp.desc()).all()
        alarms = Alarm.query.filter_by(user_id=current_user.id).all()
        return render_template('dashboard_patient.html', measurements=measurements, alarms=alarms)

@app.route('/view_patient/<int:patient_id>')
@login_required
def view_patient_dashboard(patient_id):
    if current_user.user_type != 'doctor':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    measurements = Measurement.query.filter_by(user_id=patient_id).order_by(Measurement.timestamp.desc()).all()
    alarms = Alarm.query.filter_by(user_id=patient_id).all()
    patient = User.query.get_or_404(patient_id)
    return render_template('view_patient_dashboard.html', measurements=measurements, alarms=alarms, patient=patient)

@app.route('/upload_measurement', methods=['POST'])
def upload_measurement():
    data = request.get_json()
    user = User.query.filter_by(id=data['user_id']).first()
    if user:
        measurement = Measurement(
            user_id=user.id,
            temperature=data['temperature'],
            heart_rate=data['heart_rate'],
            spo2=data['spo2']
        )
        db.session.add(measurement)
        db.session.commit()
        return jsonify({'message': 'Measurement added successfully'}), 200
    return jsonify({'message': 'User not found'}), 404

@app.route('/past_data/<int:patient_id>')
@login_required
def past_data(patient_id):
    if current_user.user_type != 'doctor' and current_user.id != patient_id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))

    measurements = Measurement.query.filter_by(user_id=patient_id).order_by(Measurement.timestamp.desc()).all()
    past_measurements = [{
        'date': m.timestamp.strftime('%Y-%m-%d'),
        'time': m.timestamp.strftime('%H:%M:%S'),
        'temperature': m.temperature,
        'heart_rate': m.heart_rate,
        'spo2': m.spo2
    } for m in measurements]

    patient = User.query.get_or_404(patient_id)
    return render_template('past_data.html', past_measurements=past_measurements, patient=patient)


# Alarm functionality
def play_sound():
    pygame.mixer.music.load('alarm_sound.wav')
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(1)

def set_alarm(alarm_time):
    while True:
        now = datetime.now().strftime("%H:%M")
        if now == alarm_time:
            play_sound()
            break
        time.sleep(30)  # Check every 30 seconds

@app.route('/set_alarm', methods=['POST'])
@login_required
def set_alarm_route():
    if current_user.user_type != 'patient':
        flash('Only patients can set alarms!', 'danger')
        return redirect(url_for('dashboard'))
    alarm_time = request.form['time']
    alarm_label = request.form['label']
    alarm = Alarm(user_id=current_user.id, time=alarm_time, label=alarm_label)
    db.session.add(alarm)
    db.session.commit()
    flash(f'Alarm set for {alarm_time}', 'success')
    threading.Thread(target=set_alarm, args=(alarm_time,)).start()
    return redirect(url_for('dashboard'))

@app.route('/delete_alarm/<int:alarm_id>', methods=['POST'])
@login_required
def delete_alarm(alarm_id):
    alarm = Alarm.query.get_or_404(alarm_id)
    if alarm.user_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(alarm)
    db.session.commit()
    flash('Alarm deleted', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
