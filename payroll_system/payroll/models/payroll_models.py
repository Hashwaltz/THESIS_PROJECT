# payroll_models.py
from main_app.extensions import db
from hr_system.hr.models.hr_models import Employee  # Use HR's Employee
from datetime import datetime

# -------------------------
# Payroll tables
# -------------------------
class Payroll(db.Model):
    """Payroll period and calculations"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    overtime_hours = db.Column(db.Float, default=0)
    overtime_pay = db.Column(db.Float, default=0)
    holiday_pay = db.Column(db.Float, default=0)
    night_differential = db.Column(db.Float, default=0)
    gross_pay = db.Column(db.Float, nullable=False)
    sss_contribution = db.Column(db.Float, default=0)
    philhealth_contribution = db.Column(db.Float, default=0)
    pagibig_contribution = db.Column(db.Float, default=0)
    tax_withheld = db.Column(db.Float, default=0)
    other_deductions = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    net_pay = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="Draft")  # Draft, Processed, Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to Employee
    employee = db.relationship('Employee', backref='payrolls', lazy=True)

    def __repr__(self):
        return f'<Payroll {self.employee_id} - {self.pay_period_start} to {self.pay_period_end}>'


class Payslip(db.Model):
    """Generated payslips"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    payroll_id = db.Column(db.Integer, db.ForeignKey('payroll.id'), nullable=False)
    payslip_number = db.Column(db.String(50), unique=True, nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    overtime_pay = db.Column(db.Float, default=0)
    holiday_pay = db.Column(db.Float, default=0)
    night_differential = db.Column(db.Float, default=0)
    allowances = db.Column(db.Float, default=0)
    gross_pay = db.Column(db.Float, nullable=False)
    sss_contribution = db.Column(db.Float, default=0)
    philhealth_contribution = db.Column(db.Float, default=0)
    pagibig_contribution = db.Column(db.Float, default=0)
    tax_withheld = db.Column(db.Float, default=0)
    other_deductions = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    net_pay = db.Column(db.Float, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Instead of FK to PayrollUser (proxy), store HR user ID
    generated_by = db.Column(db.Integer, nullable=True)

    status = db.Column(db.String(50), default="Generated")  # Generated, Sent, Downloaded
    
    # Relationships
    payroll = db.relationship('Payroll', backref='payslips', lazy=True)

    def __repr__(self):
        return f'<Payslip {self.payslip_number}>'


class Deduction(db.Model):
    """Deduction types and rates"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)  # Fixed, Percentage, Variable
    amount = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    is_mandatory = db.Column(db.Boolean, default=False)  # SSS, PhilHealth, Pag-IBIG, Tax
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Deduction {self.name}>'


class Allowance(db.Model):
    """Allowance types and amounts"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50), nullable=False)  # Fixed, Percentage, Variable
    amount = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Allowance {self.name}>'


class Tax(db.Model):
    """Tax brackets and rates"""
    id = db.Column(db.Integer, primary_key=True)
    min_income = db.Column(db.Float, nullable=False)
    max_income = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=False)
    fixed_amount = db.Column(db.Float, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tax {self.min_income} - {self.max_income}>'


class PayrollPeriod(db.Model):
    """Payroll periods (bi-monthly)"""
    id = db.Column(db.Integer, primary_key=True)
    period_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    pay_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default="Open")  # Open, Processing, Closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PayrollPeriod {self.period_name}>'
