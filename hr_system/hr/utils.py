from datetime import datetime, date, timedelta
from functools import wraps
from flask import current_app, request, jsonify
from flask_login import current_user
from hr_system.hr.models.hr_models import Department, Employee
import requests
import zipfile, tempfile, shutil, re
import pandas as pd
import os
from sqlalchemy import func, case



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

def employee_required(f):
    """Decorator to require employee role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'employee':
            return jsonify({'error': 'Employee access required'}), 403
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

def generate_employee_id(department_id):
    dept = Department.query.get(department_id)
    if not dept:
        dept_code = 'EM'
    else:
        dept_code = ''.join([word[0] for word in dept.name.split()[:2]]).upper()
        if len(dept_code) < 2:
            dept_code = dept.name[:2].upper()

    new_num = 1
    while True:
        new_id = f"{dept_code}-{new_num:04d}"
        exists = Employee.query.filter_by(employee_id=new_id).first()
        if not exists:
            break
        new_num += 1

    return new_id


def send_notification_email(to_email, subject, message):
    """Send notification email (placeholder for email functionality)"""
    print(f"Email to {to_email}: {subject} - {message}")
    return True



def get_attendance_summary(employee_id, start_date, end_date):
    """Get attendance summary for a single employee in a date range"""
    from .models.hr_models import Attendance

    query = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )

    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)

    attendances = query.all()

    return {
        'total_days': len(attendances),
        'present': len([a for a in attendances if a.status == 'Present']),
        'absent': len([a for a in attendances if a.status == 'Absent']),
        'late': len([a for a in attendances if a.status == 'Late']),
        'half_day': len([a for a in attendances if a.status == 'Half Day'])
    }

def get_attendance_chart_data(employee_id=None, start_date=None, end_date=None):
    """
    Get attendance data for charts.
    Returns dict with:
    - dates: list of dates in range
    - present, absent, late, half_day: counts per day
    """
    from .models.hr_models import Attendance
    from datetime import timedelta

    if not start_date or not end_date:
        return {
            'dates': [],
            'present': [],
            'absent': [],
            'late': [],
            'half_day': []
        }

    # Get all attendance records in the range
    query = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)

    attendances = query.all()

    # Build a dictionary keyed by date for faster lookup
    attendance_by_date = {a.date: a.status for a in attendances}

    # Prepare chart arrays
    dates = []
    present_arr = []
    absent_arr = []
    late_arr = []
    half_day_arr = []

    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        status = attendance_by_date.get(current_date, "Absent")  # Default to Absent if no record

        present_arr.append(1 if status == "Present" else 0)
        absent_arr.append(1 if status == "Absent" else 0)
        late_arr.append(1 if status == "Late" else 0)
        half_day_arr.append(1 if status == "Half Day" else 0)

        current_date += timedelta(days=1)

    return {
        'dates': dates,
        'present': present_arr,
        'absent': absent_arr,
        'late': late_arr,
        'half_day': half_day_arr
    }



def get_department_attendance_summary(department_id, start_date, end_date):
    """Get aggregated attendance summary for a department in a date range"""
    from .models.hr_models import Attendance, Employee

    query = Attendance.query.join(Employee).filter(
        Employee.department_id == department_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )

    # Totals
    total_present = query.filter(Attendance.status == "Present").count()
    total_absent = query.filter(Attendance.status == "Absent").count()
    total_late = query.filter(Attendance.status == "Late").count()
    total_half_day = query.filter(Attendance.status == "Half Day").count()

    # Daily breakdown for charts
    daily_records = (
        query.with_entities(
            Attendance.date,
            func.sum(case((Attendance.status == "Present", 1), else_=0)),
            func.sum(case((Attendance.status == "Absent", 1), else_=0)),
            func.sum(case((Attendance.status == "Late", 1), else_=0))
        )
        .group_by(Attendance.date)
        .order_by(Attendance.date)
        .all()
    )


    return {
        "total_present": total_present,
        "total_absent": total_absent,
        "total_late": total_late,
        "total_half_day": total_half_day,
        "dates": [str(r[0]) for r in daily_records],
        "present_counts": [int(r[1]) for r in daily_records],
        "absent_counts": [int(r[2]) for r in daily_records],
        "late_counts": [int(r[3]) for r in daily_records],
    }


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




# ----------------- HELPER FUNCTIONS -----------------
def unlock_xlsx(file_path, unlocked_path):
    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            z.extractall(tmpdir)

        # remove protection tags
        pat = re.compile(r"<(sheetProtection|workbookProtection)\b[^>]*/>", re.IGNORECASE)
        targets = []

        wb = os.path.join(tmpdir, "xl", "workbook.xml")
        if os.path.exists(wb):
            targets.append(wb)

        wsdir = os.path.join(tmpdir, "xl", "worksheets")
        if os.path.isdir(wsdir):
            for f in os.listdir(wsdir):
                if f.endswith(".xml"):
                    targets.append(os.path.join(wsdir, f))

        for f in targets:
            with open(f, "r", encoding="utf-8") as fh:
                txt = fh.read()
            new = pat.sub("", txt)
            if new != txt:
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(new)

        # rezip as unlocked xlsx
        with zipfile.ZipFile(unlocked_path, "w", zipfile.ZIP_DEFLATED) as z:
            for folder, _, files in os.walk(tmpdir):
                for file in files:
                    full = os.path.join(folder, file)
                    arc = os.path.relpath(full, tmpdir).replace("\\", "/")
                    z.write(full, arc)
    finally:
        shutil.rmtree(tmpdir)




def load_excel_to_df(file_path):
    unlocked_path = file_path.replace(".xlsx", "_unlocked.xlsx")
    try:
        unlock_xlsx(file_path, unlocked_path)
        df = pd.read_excel(unlocked_path)
    except Exception:
        df = pd.read_excel(file_path)
    return df