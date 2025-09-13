from . import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="employee")

    department_id = db.Column(
        db.Integer,
        db.ForeignKey('department.id', name='fk_user_department_id')
    )
    position = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    managed_department = db.relationship("Department", back_populates="head", uselist=False)
    employee_profile = db.relationship("Employee", back_populates="user", uselist=False)
    approved_leaves = db.relationship("Leave", back_populates="approver", lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
