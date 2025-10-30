from main_app.extensions import db
from datetime import datetime, date, time

# =========================================================
# HR MODELS
# =========================================================

class Employee(db.Model):
    __tablename__ = "employee"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_employee_user_id'), unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', name='fk_employee_department_id'))
    position_id = db.Column(db.Integer, db.ForeignKey('position.id', name='fk_employee_position_id'))

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    salary = db.Column(db.Float)
    date_hired = db.Column(db.Date, nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="employee_profile", uselist=False)
    department = db.relationship("Department", back_populates="employees", foreign_keys=[department_id])
    position = db.relationship("Position", back_populates="employees", foreign_keys=[position_id])
    attendances = db.relationship("Attendance", back_populates="employee", lazy=True)
    leaves = db.relationship("Leave", back_populates="employee", lazy=True)

    # Payroll-related relationships
    payrolls = db.relationship("Payroll", back_populates="employee", lazy=True)
    payslips = db.relationship("Payslip", back_populates="employee", lazy=True)
    employee_deductions = db.relationship("EmployeeDeduction", back_populates="employee", lazy=True, cascade="all, delete-orphan")
    employee_allowances = db.relationship("EmployeeAllowance", back_populates="employee", lazy=True, cascade="all, delete-orphan")

    # ✅ Convenient relationships (view-only)
    deductions = db.relationship(
        "Deduction",
        secondary="employee_deductions",
        viewonly=True,
        lazy="joined"
    )
    allowances = db.relationship(
        "Allowance",
        secondary="employee_allowances",
        viewonly=True,
        lazy="joined"
    )

    def __repr__(self):
        return f"<Employee {self.employee_id}: {self.first_name} {self.last_name}>"

    def get_full_name(self):
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()


# =========================================================
# ATTENDANCE
# =========================================================
class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    time_in = db.Column(db.Time)
    time_out = db.Column(db.Time)
    status = db.Column(db.String(50), default="Present")
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance {self.employee_id} - {self.date}>"

    def check_late(self):
        """Automatically mark as late if time_in is after 8:00 AM."""
        if self.time_in and self.time_in > time(8, 0):  # 8:00 AM cutoff
            self.status = "Late"
            self.remarks = f"Late - Time In: {self.time_in.strftime('%I:%M %p')}"
        else:
            self.status = "Present"


# =========================================================
# LEAVE
# =========================================================
class Leave(db.Model):
    __tablename__ = "leave"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    leave_type_id = db.Column(db.Integer, db.ForeignKey("leave_type.id", name="fk_leave_leave_type_id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending")
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id", name="fk_leave_approved_by"))
    approved_at = db.Column(db.DateTime)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="leaves")
    leave_type = db.relationship("LeaveType", back_populates="leaves", foreign_keys=[leave_type_id])
    approver = db.relationship("User", back_populates="approved_leaves", foreign_keys=[approved_by])
    
    def __repr__(self):
        return f"<Leave {self.employee_id} - {self.leave_type_id}>"


# =========================================================
# DEPARTMENT / POSITION / LEAVE TYPE
# =========================================================
class Department(db.Model):
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    head_id = db.Column(db.Integer, db.ForeignKey("user.id", name="fk_department_head_id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    head = db.relationship("User", back_populates="managed_department", foreign_keys=[head_id])
    employees = db.relationship("Employee", back_populates="department", lazy=True)
    positions = db.relationship("Position", back_populates="department", lazy=True)

    def __repr__(self):
        return f"<Department {self.name}>"


class Position(db.Model):
    __tablename__ = "position"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id", name="fk_position_department_id"))

    department = db.relationship("Department", back_populates="positions", foreign_keys=[department_id])
    employees = db.relationship("Employee", back_populates="position", lazy=True)

    def __repr__(self):
        return f"<Position {self.name}>"


class LeaveType(db.Model):
    __tablename__ = 'leave_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)

    leaves = db.relationship('Leave', back_populates='leave_type', lazy=True)

    def __repr__(self):
        return f'<LeaveType {self.name}>'
