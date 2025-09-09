from datetime import datetime, date, timedelta
from functools import wraps
from flask import current_app, request, jsonify
from flask_login import current_user
import requests

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Decorator to require staff role or higher"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'staff']:
            return jsonify({'error': 'Staff access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def calculate_sss_contribution(basic_salary):
    """Calculate SSS contribution based on salary"""
    # SSS contribution table (simplified)
    if basic_salary <= 1000:
        return 50.00
    elif basic_salary <= 2000:
        return 100.00
    elif basic_salary <= 3000:
        return 150.00
    elif basic_salary <= 4000:
        return 200.00
    elif basic_salary <= 5000:
        return 250.00
    elif basic_salary <= 6000:
        return 300.00
    elif basic_salary <= 7000:
        return 350.00
    elif basic_salary <= 8000:
        return 400.00
    elif basic_salary <= 9000:
        return 450.00
    elif basic_salary <= 10000:
        return 500.00
    else:
        return 500.00  # Maximum SSS contribution

def calculate_philhealth_contribution(basic_salary):
    """Calculate PhilHealth contribution based on salary"""
    # PhilHealth contribution is 3% of basic salary
    return basic_salary * 0.03

def calculate_pagibig_contribution(basic_salary):
    """Calculate Pag-IBIG contribution based on salary"""
    # Pag-IBIG contribution is 2% of basic salary
    return basic_salary * 0.02

def calculate_tax_withheld(gross_pay):
    """Calculate tax withheld based on gross pay"""
    # Simplified tax calculation
    if gross_pay <= 250000:
        return 0  # No tax for income up to 250,000
    elif gross_pay <= 400000:
        return (gross_pay - 250000) * 0.20
    elif gross_pay <= 800000:
        return 30000 + (gross_pay - 400000) * 0.25
    elif gross_pay <= 2000000:
        return 130000 + (gross_pay - 800000) * 0.30
    elif gross_pay <= 8000000:
        return 490000 + (gross_pay - 2000000) * 0.32
    else:
        return 2410000 + (gross_pay - 8000000) * 0.35

def calculate_overtime_pay(basic_salary, overtime_hours):
    """Calculate overtime pay"""
    hourly_rate = basic_salary / 8 / 22  # Assuming 8 hours per day, 22 working days per month
    return overtime_hours * hourly_rate * 1.25  # 25% overtime premium

def calculate_holiday_pay(basic_salary, holiday_hours):
    """Calculate holiday pay"""
    hourly_rate = basic_salary / 8 / 22
    return holiday_hours * hourly_rate * 2.0  # Double pay for holidays

def calculate_night_differential(basic_salary, night_hours):
    """Calculate night differential pay"""
    hourly_rate = basic_salary / 8 / 22
    return night_hours * hourly_rate * 0.10  # 10% night differential

def generate_payslip_number(employee_id, pay_period_start):
    """Generate unique payslip number"""
    year = pay_period_start.year
    month = pay_period_start.month
    return f"PS{year}{month:02d}{employee_id:04d}"

def sync_employee_from_hr(employee_id):
    """Sync employee data from HR system"""
    try:
        hr_url = current_app.config.get('HR_SYSTEM_URL', 'http://localhost:5001')
        response = requests.get(
            f"{hr_url}/api/hr/employees/{employee_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']
        return None
    except requests.RequestException:
        return None

def sync_all_employees_from_hr():
    """Sync all employees from HR system"""
    try:
        hr_url = current_app.config.get('HR_SYSTEM_URL', 'http://localhost:5001')
        response = requests.get(
            f"{hr_url}/api/hr/employees",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']
        return []
    except requests.RequestException:
        return []

def format_currency(amount):
    """Format amount as currency"""
    return f"₱{amount:,.2f}"

def get_payroll_periods():
    """Get current payroll periods"""
    from payroll.models.payroll_models import PayrollPeriod
    return PayrollPeriod.query.filter_by(status='Open').all()

def calculate_payroll_summary(period_id, department=None):
    """Calculate payroll summary for a period"""
    from payroll.models.payroll_models import Payroll, Employee
    
    query = Payroll.query.filter_by(id=period_id)
    
    if department:
        query = query.join(Employee).filter(Employee.department == department)
    
    payrolls = query.all()
    
    summary = {
        'total_employees': len(payrolls),
        'total_gross_pay': sum(p.gross_pay for p in payrolls),
        'total_deductions': sum(p.total_deductions for p in payrolls),
        'total_net_pay': sum(p.net_pay for p in payrolls),
        'total_sss': sum(p.sss_contribution for p in payrolls),
        'total_philhealth': sum(p.philhealth_contribution for p in payrolls),
        'total_pagibig': sum(p.pagibig_contribution for p in payrolls),
        'total_tax': sum(p.tax_withheld for p in payrolls)
    }
    
    return summary

def send_payslip_notification(employee_email, payslip_number):
    """Send payslip notification email"""
    # This would integrate with your email service
    print(f"Payslip notification sent to {employee_email}: {payslip_number}")
    return True

def generate_payroll_report(period_id, format='pdf'):
    """Generate payroll report"""
    # This would generate actual reports
    # For now, return a placeholder
    return f"Payroll report for period {period_id} in {format} format"

def get_current_payroll_period():
    """Get current payroll period"""
    from payroll.models.payroll_models import PayrollPeriod
    today = date.today()
    
    period = PayrollPeriod.query.filter(
        PayrollPeriod.start_date <= today,
        PayrollPeriod.end_date >= today,
        PayrollPeriod.status == 'Open'
    ).first()
    
    return period

def create_payroll_period(period_name, start_date, end_date, pay_date):
    """Create a new payroll period"""
    from payroll.models.payroll_models import PayrollPeriod
    from payroll import db
    
    period = PayrollPeriod(
        period_name=period_name,
        start_date=start_date,
        end_date=end_date,
        pay_date=pay_date
    )
    
    try:
        db.session.add(period)
        db.session.commit()
        return period
    except Exception as e:
        db.session.rollback()
        return None

def process_payroll_for_employee(employee_id, period_id):
    """Process payroll for a specific employee"""
    from payroll.models.payroll_models import Employee, Payroll, PayrollPeriod
    from payroll import db
    
    employee = Employee.query.get(employee_id)
    period = PayrollPeriod.query.get(period_id)
    
    if not employee or not period:
        return None
    
    # Calculate basic salary (assuming monthly)
    basic_salary = employee.basic_salary
    
    # Calculate overtime pay (if any)
    overtime_hours = 0  # This would come from attendance system
    overtime_pay = calculate_overtime_pay(basic_salary, overtime_hours)
    
    # Calculate holiday pay (if any)
    holiday_pay = 0  # This would come from attendance system
    
    # Calculate night differential (if any)
    night_differential = 0  # This would come from attendance system
    
    # Calculate gross pay
    gross_pay = basic_salary + overtime_pay + holiday_pay + night_differential
    
    # Calculate deductions
    sss_contribution = calculate_sss_contribution(basic_salary)
    philhealth_contribution = calculate_philhealth_contribution(basic_salary)
    pagibig_contribution = calculate_pagibig_contribution(basic_salary)
    tax_withheld = calculate_tax_withheld(gross_pay)
    
    total_deductions = sss_contribution + philhealth_contribution + pagibig_contribution + tax_withheld
    
    # Calculate net pay
    net_pay = gross_pay - total_deductions
    
    # Create payroll record
    payroll = Payroll(
        employee_id=employee_id,
        pay_period_start=period.start_date,
        pay_period_end=period.end_date,
        basic_salary=basic_salary,
        overtime_hours=overtime_hours,
        overtime_pay=overtime_pay,
        holiday_pay=holiday_pay,
        night_differential=night_differential,
        gross_pay=gross_pay,
        sss_contribution=sss_contribution,
        philhealth_contribution=philhealth_contribution,
        pagibig_contribution=pagibig_contribution,
        tax_withheld=tax_withheld,
        total_deductions=total_deductions,
        net_pay=net_pay
    )
    
    try:
        db.session.add(payroll)
        db.session.commit()
        return payroll
    except Exception as e:
        db.session.rollback()
        return None


