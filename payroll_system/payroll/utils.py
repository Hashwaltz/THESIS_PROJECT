from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from payroll_system.payroll.models.user import PayrollUser
from g4f.client import Client
#from g4f.providers import Aichat
from payroll_system.payroll.models.payroll_models import (
    Employee, Payroll, Payslip, PayrollPeriod, Deduction, Allowance, Tax, EmployeeDeduction, EmployeeAllowance
)
from payroll_system.payroll.forms import (
    PayrollPeriodForm, PayrollForm, PayslipForm,
    DeductionForm, AllowanceForm, TaxForm, PayrollSummaryForm
)
from payroll_system.payroll import db
from hr_system.hr.models.user import User
from hr_system.hr.models.hr_models import Department, Employee as HREmployee, Attendance
from datetime import datetime, date, timedelta
import os
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload
import io
import pandas as pd

import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
from functools import wraps
from flask import current_app, request, jsonify, abort

import requests



HR_API_URL = "http://localhost:5000/api"  # 🔑 Change to your HR system URL
def get_user_from_hr(hr_user_id):
    """Fetch HR user data and create PayrollUser if not exists."""
    try:
        response = requests.get(f"{HR_API_URL}/users/{hr_user_id}")
        if response.status_code != 200:
            return None

        data = response.json().get("data")
        if not data:
            return None

        user = PayrollUser.query.filter_by(email=data['email']).first()
        if not user:
            user = PayrollUser(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                role=data['role']
            )
            db.session.add(user)
            db.session.commit()
        return user

    except Exception as e:
        print("Error in get_user_from_hr:", e)
        return None

# ================
# Role Decorators
# ================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role.lower() not in ["staff", "officer", "dept_head", "admin"]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function



def compute_payroll_from_excel(row):
    """
    Compute payroll using the logic shown in the sample payroll Excel file
    and standard PH contribution formulas.
    """

    # --- 1️⃣ Basic Pay ---
    basic_salary = row['Monthly Rate']  # Monthly salary
    daily_rate = basic_salary / 22  # assuming 22 working days
    hourly_rate = daily_rate / 8

    overtime_hours = row.get('Overtime Hours', 0)
    holiday_hours = row.get('Holiday Hours', 0)
    night_hours = row.get('Night Hours', 0)

    # --- 2️⃣ Earnings ---
    overtime_pay = overtime_hours * hourly_rate * 1.25          # 25% OT premium
    holiday_pay = holiday_hours * hourly_rate * 2.0              # 200% for regular holiday
    night_differential = night_hours * hourly_rate * 0.10        # 10% of hourly rate

    gross_pay = basic_salary + overtime_pay + holiday_pay + night_differential

    # --- 3️⃣ Mandatory Deductions (estimated PH computation) ---
    sss_contribution = calculate_sss_contribution(basic_salary)
    philhealth_contribution = calculate_philhealth_contribution(basic_salary)
    pagibig_contribution = calculate_pagibig_contribution(basic_salary)
    tax_withheld = calculate_tax_withheld(gross_pay)

    # --- 4️⃣ Totals ---
    total_deductions = sss_contribution + philhealth_contribution + pagibig_contribution + tax_withheld
    net_pay = gross_pay - total_deductions

    return {
        "basic_salary": basic_salary,
        "overtime_pay": overtime_pay,
        "holiday_pay": holiday_pay,
        "night_differential": night_differential,
        "gross_pay": gross_pay,
        "sss_contribution": sss_contribution,
        "philhealth_contribution": philhealth_contribution,
        "pagibig_contribution": pagibig_contribution,
        "tax_withheld": tax_withheld,
        "total_deductions": total_deductions,
        "net_pay": net_pay
    }


# === Helper Functions ===
def calculate_sss_contribution(salary):
    """Approximate SSS contribution (2025 rates)."""
    if salary <= 3250:
        return 135
    elif salary >= 24750:
        return 1125
    else:
        return 0.045 * salary  # 4.5% (employee share)

def calculate_philhealth_contribution(salary):
    """PhilHealth 2025: 5% of monthly basic salary, divided equally (employee share = 2.5%)."""
    base = min(max(salary, 10000), 100000)  # salary floor/ceiling
    return (base * 0.05) / 2

def calculate_pagibig_contribution(salary):
    """Pag-IBIG: 1% or 2% depending on salary."""
    if salary <= 1500:
        return salary * 0.01
    else:
        return salary * 0.02

def calculate_tax_withheld(gross_pay):
    """Approximate tax using PH TRAIN law brackets."""
    if gross_pay <= 20833:
        return 0
    elif gross_pay <= 33333:
        return (gross_pay - 20833) * 0.20
    elif gross_pay <= 66667:
        return 2500 + (gross_pay - 33333) * 0.25
    elif gross_pay <= 166667:
        return 10833 + (gross_pay - 66667) * 0.30
    elif gross_pay <= 666667:
        return 40833.33 + (gross_pay - 166667) * 0.32
    else:
        return 200833.33 + (gross_pay - 666667) * 0.35

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


def get_payroll_summary():
    """Return summary stats and department data."""
    total_employees = Employee.query.count()
    total_payrolls = Payroll.query.count()
    total_net_pay = Payroll.query.with_entities(func.sum(Payroll.net_pay)).scalar() or 0
    pending = Payroll.query.filter_by(status="Pending").count()
    approved = Payroll.query.filter_by(status="Approved").count()
    rejected = Payroll.query.filter_by(status="Rejected").count()

    dept_data = []
    departments = Department.query.all()
    for dept in departments:
        dept_payrolls = Payroll.query.join(Employee).filter(Employee.department_id == dept.id).count()
        dept_net = Payroll.query.join(Employee).filter(Employee.department_id == dept.id).with_entities(func.sum(Payroll.net_pay)).scalar() or 0
        dept_data.append({'department': dept.name, 'payrolls': dept_payrolls, 'net_pay': dept_net})

    summary = {
        'total_employees': total_employees,
        'total_payrolls': total_payrolls,
        'total_net_pay': total_net_pay,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'departments': dept_data
    }
    return summary

def generate_ai_report(summary):
    """Use g4f client to generate AI insights."""
    client = Client()
    dept_summary = ", ".join([f"{d['department']} ({d['payrolls']} payrolls, ₱{d['net_pay']:,.2f})" for d in summary['departments']])
    features = """
    Features:
    - Dashboard overview
    - Employee Payroll Details
    - Add Employee Payroll
    - Payroll Period Management
    - Process Payroll
    - View Payroll History
    - Manage Deductions & Allowances
    - Generate, Approve, Distribute Payslips
    - Payroll Reports
    """

    prompt = f"""
    Payroll Stats:
    Total employees: {summary['total_employees']}
    Total payroll entries: {summary['total_payrolls']}
    Total net pay: ₱{summary['total_net_pay']:,.2f}
    Pending: {summary['pending']}
    Approved: {summary['approved']}
    Rejected: {summary['rejected']}
    Department summary: {dept_summary}

    Based on the payroll system features:
    {features}

    Generate a management report with:
    1. Insights and trends
    2. Department highlights
    3. Suggestions for improvement
    4. Key takeaways
    """

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        web_search=False
    )
    return response.choices[0].message.content

def generate_department_chart(summary):
    """Generate bar chart for departments' net pay."""
    df = pd.DataFrame(summary['departments'])
    plt.figure(figsize=(8,5))
    plt.bar(df['department'], df['net_pay'], color='skyblue')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Net Pay (₱)")
    plt.title("Department Net Pay Summary")
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf





def generate_payroll_insights():
    client = Client()

    # Aggregate payroll data
    total_employees = Employee.query.count()
    total_payrolls = Payroll.query.count()
    total_net_pay = Payroll.query.with_entities(func.sum(Payroll.net_pay)).scalar() or 0
    pending_payslips = Payroll.query.filter_by(status="Pending").count()
    approved_payslips = Payroll.query.filter_by(status="Approved").count()
    rejected_payslips = Payroll.query.filter_by(status="Rejected").count()

    # Department level summary
    dept_summary = []
    departments = Department.query.all()
    for dept in departments:
        dept_payrolls = Payroll.query.join(Employee).filter(Employee.department_id == dept.id).count()
        dept_net_pay = Payroll.query.join(Employee).filter(Employee.department_id == dept.id).with_entities(func.sum(Payroll.net_pay)).scalar() or 0
        dept_summary.append(f"{dept.name}: {dept_payrolls} payrolls, ₱{dept_net_pay:,.2f} net pay")

    # Features/Functions context
    features = """
    Features to consider in insights:
    - Dashboard: overview and quick insights
    - View Employee Payroll Details: search/filter by employee
    - Add Employees Payroll: manual input for salary, deductions, allowances
    - Payroll Period Management: cutoff periods
    - Process Payroll: auto compute salaries
    - View Payroll History: reference and audit past payrolls
    - Manage Deductions & Allowances: SSS, PhilHealth, Pag-IBIG, bonuses
    - Generate, Approve, Distribute Payslips
    - Payroll reports: summary, leave, earnings, deduction, compliance
    """

    prompt = f"""
    I have payroll data with the following stats:
    - Total employees: {total_employees}
    - Total payroll entries: {total_payrolls}
    - Total net pay disbursed: ₱{total_net_pay:,.2f}
    - Pending payslips: {pending_payslips}
    - Approved payslips: {approved_payslips}
    - Rejected payslips: {rejected_payslips}
    - Department summary:
      {', '.join(dept_summary)}

    Based on the payroll system features:
    {features}

    Generate a concise management report with:
    1. Insights and trends on payroll efficiency
    2. Departmental highlights
    3. Suggestions for improvement
    4. Key takeaways for management
    """

    # Generate AI report
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        web_search=False
    )

    insights = response.choices[0].message.content
    return insights

def get_current_payroll_period():
    """Get current payroll period"""
    today = date.today()
    
    period = PayrollPeriod.query.filter(
        PayrollPeriod.start_date <= today,
        PayrollPeriod.end_date >= today,
        PayrollPeriod.status == 'Open'
    ).first()
    
    return period

def create_payroll_period(period_name, start_date, end_date, pay_date):
    """Create a new payroll period"""
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


