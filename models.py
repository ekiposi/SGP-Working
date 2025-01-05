from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import qrcode
import random
import string

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    employee = db.relationship('Employee', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pluri_id = db.Column(db.String(20), unique=True, nullable=False)
    photo = db.Column(db.String(150), unique=True, nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    hire_date = db.Column(db.Date, nullable=False)
    dob = db.Column(db.Date, nullable=False)
    qr_data = db.Column(db.String(200), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    attendances = db.relationship('Attendance', backref='employee', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @staticmethod
    def generate_pluri_id():
        # Generate a random 6-character ID
        chars = string.ascii_uppercase + string.digits
        while True:
            pluri_id = ''.join(random.choices(chars, k=6))
            if not Employee.query.filter_by(pluri_id=pluri_id).first():
                return pluri_id

    def generate_qr_code(self):
        if not self.qr_data:
            self.qr_data = f"EMP_{self.pluri_id}_{random.randint(1000, 9999)}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = f"uploads/qrcodes/qr_{self.pluri_id}.png"
        img.save(os.path.join('static', qr_path))
        return qr_path

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    check_out = db.Column(db.DateTime)
    total_hours = db.Column(db.Float)