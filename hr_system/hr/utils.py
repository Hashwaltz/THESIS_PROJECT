from datetime import datetime, date, timedelta
from functools import wraps
from flask import current_app, request, jsonify
from flask_login import current_user
from hr_system.hr.models.hr_models import Department
import requests



# ------------------------
# Role-based decorators
# ------------------------

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def hr_officer_required(f):
    """Decorator to require HR officer role or higher"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'officer']:
            return jsonify({'error': 'HR Officer access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def dept_head_required(f):
    """Decorator to require department head role or higher"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'officer', 'dept_head']:
            return jsonify({'error': 'Department Head access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ------------------------
# Date & Leave Utilities
# ------------------------

def calculate_working_days(start_date, end_date):
    """Calculate working days between two dates (excluding weekends)"""
    if start_date > end_date:
        return 0
    
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days

def generate_employee_id(department_id, last_employee_id=None):
   
    # Get the department from DB
    dept = Department.query.get(department_id)
    if not dept:
        dept_code = 'EM'  # default if not found
    else:
        # Use first 2-3 letters of department name as code
        dept_code = ''.join([word[0] for word in dept.name.split()[:2]]).upper()
        if len(dept_code) < 2:
            dept_code = dept.name[:2].upper()

    if last_employee_id:
        try:
            last_num = int(last_employee_id.split('-')[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1

    return f"{dept_code}-{new_num:04d}"




def send_notification_email(to_email, subject, message):
    """Send notification email (placeholder for email functionality)"""
    print(f"Email to {to_email}: {subject} - {message}")
    return True

def get_attendance_summary(employee_id, start_date, end_date):
    """Get attendance summary for an employee in a date range"""
    # ✅ Relative import
    from .models.hr_models import Attendance
    
    query = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    
    attendances = query.all()
    
    summary = {
        'total_days': len(attendances),
        'present': len([a for a in attendances if a.status == 'Present']),
        'absent': len([a for a in attendances if a.status == 'Absent']),
        'late': len([a for a in attendances if a.status == 'Late']),
        'half_day': len([a for a in attendances if a.status == 'Half Day'])
    }
    
    return summary

def get_leave_balance(employee_id, leave_type):
    """Get leave balance for an employee (placeholder)"""
    default_balances = {
        'Sick': 15,
        'Vacation': 20,
        'Personal': 5,
        'Emergency': 3,
        'Maternity': 90,
        'Paternity': 7
    }
    return default_balances.get(leave_type, 0)

def sync_with_payroll(employee_data):
    """Sync employee data with payroll system"""
    try:
        payroll_url = current_app.config.get('PAYROLL_SYSTEM_URL', 'http://localhost:5000')
        response = requests.post(
            f"{payroll_url}/api/payroll/employee/sync",
            json=employee_data,
            timeout=30
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

def format_currency(amount):
    """Format amount as currency"""
    return f"₱{amount:,.2f}"

def get_current_month_range():
    """Get start and end dates of current month"""
    today = date.today()
    start_date = date(today.year, today.month, 1)
    
    if today.month == 12:
        end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date
