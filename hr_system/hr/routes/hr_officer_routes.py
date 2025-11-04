from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department, Position
from ..forms import EmployeeForm, AttendanceForm, LeaveForm
from ..utils import hr_officer_required, get_attendance_summary, get_current_month_range
from .. import db
from sqlalchemy.orm import joinedload
import os
from werkzeug.utils import secure_filename
import pandas as pd
import uuid


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "hr_static")

hr_officer_bp = Blueprint(
    'officer',
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/hr/static'
    )


# --- OFFICER DASHBOARD ---
@hr_officer_bp.route('/dashboard')
@login_required
@hr_officer_required
def hr_dashboard():
    today = datetime.now().date()

    # --- Info Box Data (Today's Data) ---
    today_attendance_records = Attendance.query.filter_by(date=today).all()
    present_count_today = len([r for r in today_attendance_records if r.status == "Present"])
    absent_count_today = len([r for r in today_attendance_records if r.status == "Absent"])
    
    total_active_employees = Employee.query.filter_by(active=True).count() or 0

    # --- Graph Data (Current Month Data) ---
    start_date, end_date = get_current_month_range()
    
    monthly_dates = []
    monthly_present_counts = []
    monthly_absent_counts = []
    monthly_late_counts = []
    
    current_date = start_date
    while current_date <= end_date:
        records_on_date = Attendance.query.filter_by(date=current_date).all()
        monthly_dates.append(current_date.strftime("%b %d")) # e.g. Sep 01
        monthly_present_counts.append(len([r for r in records_on_date if r.status == "Present"]))
        monthly_absent_counts.append(len([r for r in records_on_date if r.status == "Absent"]))
        monthly_late_counts.append(len([r for r in records_on_date if r.status == "Late"]))
        current_date += timedelta(days=1)

    # --- Daily Reminders (Example) ---
    reminders = []
    # Example reminder: check for pending leave requests
    pending_leaves_count = Leave.query.filter_by(status='Pending').count()
    if pending_leaves_count > 0:
        reminders.append(f"You have {pending_leaves_count} pending leave requests to review.")
    
    return render_template(
        'hr/officer/officer_dashboard.html',
        present_count=present_count_today, 
        absent_count=absent_count_today,   
        total_users=total_active_employees,
        # Data for the graph
        monthly_dates=monthly_dates,
        monthly_present_counts=monthly_present_counts,
        monthly_absent_counts=monthly_absent_counts,
        monthly_late_counts=monthly_late_counts,
        reminders=reminders
    )


@hr_officer_bp.route('/employees')
@login_required
@hr_officer_required
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    department = request.args.get('department', '')

    # Base query (only active employees)
    query = Employee.query.filter_by(active=True)

    # Search by name or employee_id
    if search:
        query = query.filter(
            (Employee.first_name.ilike(f"%{search}%")) |
            (Employee.last_name.ilike(f"%{search}%")) |
            (Employee.employee_id.ilike(f"%{search}%"))
        )

    # Filter by department if selected
    if department:
        query = query.filter_by(department_id=department)

    # ✅ Sort employees in ascending order by last name, then first name
    query = query.order_by(Employee.last_name.asc(), Employee.first_name.asc())

    # Pagination
    employees = query.paginate(page=page, per_page=10, error_out=False)

    # Fetch all departments for dropdown
    departments = Department.query.all()

    return render_template(
        'hr/officer/officer_view_emp.html',
        employees=employees,
        search=search,
        selected_department=department,
        departments=departments
    )


# ==========================
# HR Officer - Edit Employee (Limited Permissions)
# ==========================
@hr_officer_bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
@hr_officer_required  
def edit_employee(employee_id):
    """HR Officer can edit limited employee info"""
    employee = Employee.query.get_or_404(employee_id)
    departments = Department.query.all()
    positions = Position.query.all()

    if request.method == "POST":
        try:
            # ✅ Update editable fields
            employee.phone = request.form.get("phone")
            employee.address = request.form.get("address")
            employee.marital_status = request.form.get("marital_status")
            employee.emergency_contact = request.form.get("emergency_contact")
            employee.emergency_phone = request.form.get("emergency_phone")

            employee.updated_at = datetime.utcnow()
            db.session.commit()

            # ✅ Return SweetAlert-friendly JSON response
            return jsonify({
                "status": "success",
                "message": "Employee contact details updated successfully!"
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {employee_id}: {e}")
            return jsonify({
                "status": "error",
                "message": "Error updating employee. Please try again."
            }), 500

    return render_template(
        "hr/officer/officer_edit.html",
        employee=employee,
        departments=departments,
        positions=positions
    )

@hr_officer_bp.route('/attendance')
@login_required
@hr_officer_required
def attendance():
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    employee_filter = request.args.get('employee', '')
    department_filter = request.args.get('department', '')

    query = Attendance.query.options(joinedload(Attendance.employee).joinedload(Employee.department))

    # --- Apply Filters ---
    # Filter by Date Range
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date.between(start, end))
        except ValueError:
            flash('Invalid date format.', 'danger')

    # Filter by Employee
    if employee_filter:
        query = query.filter(Attendance.employee_id == employee_filter)

    # Filter by Department
    if department_filter:
        query = query.join(Employee).filter(Employee.department_id == department_filter)

    attendances = query.order_by(Attendance.date.desc(), Attendance.time_in.desc())\
                       .paginate(page=page, per_page=10, error_out=False)

    employees = Employee.query.filter_by(active=True).order_by(Employee.first_name).all()
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        'hr/officer/officer_view_attend.html',
        attendances=attendances,
        employees=employees,
        departments=departments,
        start_date=start_date,
        end_date=end_date,
        employee_filter=employee_filter,
        department_filter=department_filter
    )


# ----------------- CONFIG -----------------
OFFICER_ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
OFFICER_UPLOAD_FOLDER = "uploads/attendance/officer"

def allowed_officer_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in OFFICER_ALLOWED_EXTENSIONS


# ----------------- UPLOAD & PREVIEW -----------------
@hr_officer_bp.route('/attendance/add_bulk', methods=['GET', 'POST'])
@login_required
@hr_officer_required
def add_bulk_attendance():
    preview_data = []

    if request.method == 'POST' and 'file' in request.files:
        file = request.files.get("file")
        if not file or not allowed_officer_file(file.filename):
            flash("Please upload a valid Excel file (.xls or .xlsx).", "danger")
            return redirect(request.url)

        # Save uploaded file
        filename = secure_filename(file.filename)
        os.makedirs(OFFICER_UPLOAD_FOLDER, exist_ok=True)
        filepath = os.path.join(OFFICER_UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{filename}")
        file.save(filepath)

        try:
            df = pd.read_excel(filepath, header=None)
            records = []
            current_id, current_name, current_dept = None, None, None
            attendance_date = None

            for _, row in df.iterrows():
                line = " ".join(str(x) for x in row if str(x) != "nan").strip()
                if not line or "tabling date" in line.lower():
                    continue

                # Extract attendance date
                if "Attendance date:" in line:
                    attendance_date = line.split(":")[-1].strip()
                    continue

                # Extract employee info
                if "User ID" in line and "Name" in line:
                    uid_part = line.split("User ID:")[-1]
                    name_part = uid_part.split("Name:")
                    id_value = name_part[0].strip() if len(name_part) > 0 else None

                    if len(name_part) > 1:
                        name_dept_part = name_part[1].split("Department:")
                        name = name_dept_part[0].strip()
                        dept = name_dept_part[1].strip() if len(name_dept_part) > 1 else "Unknown"
                    else:
                        name, dept = "Unknown", "Unknown"

                    current_id, current_name, current_dept = id_value, name, dept
                    continue

                # Extract times
                if ":" in line:
                    times = line.split()
                    time_in = times[0] if len(times) > 0 else None
                    time_out = times[1] if len(times) > 1 else None

                    day_value = attendance_date or datetime.now().date().isoformat()

                    # Check if employee exists
                    try:
                        emp_id_int = int(float(current_id))
                        emp_match = Employee.query.get(emp_id_int)
                        matched = True if emp_match else False
                    except:
                        matched = False

                    records.append({
                        "Employee ID": current_id,
                        "Name": current_name or "Unknown",
                        "Department": current_dept or "Unknown",
                        "Day": day_value,
                        "Time In": time_in,
                        "Time Out": time_out,
                        "Matched": matched
                    })

            if not records:
                flash("No valid attendance records found in file. Please check the format.", "danger")
                return redirect(request.url)

            session['officer_attendance_preview'] = records
            preview_data = records
            flash("Preview loaded. Please confirm import.", "info")

        except Exception as e:
            flash(f"Error reading Excel file: {e}", "danger")
            return redirect(request.url)

    return render_template('hr/officer/officer_import_attendance.html', preview=preview_data)


# ----------------- CONFIRM IMPORT -----------------
@hr_officer_bp.route('/attendance/confirm_bulk', methods=['POST'])
@login_required
@hr_officer_required
def confirm_bulk_attendance():
    records = session.get('officer_attendance_preview', [])
    if not records:
        flash("No attendance records to import.", "danger")
        return redirect(url_for('officer.add_bulk_attendance'))

    imported_count = 0

    for row in records:
        if not row.get("Matched"):
            continue  # Only import matched employees

        day = row.get("Day")
        if not day or "Tabling" in str(day):
            continue

        # Handle date ranges
        date_list = []
        try:
            if "~" in day:
                start_str, end_str = day.split("~")
                start_date = pd.to_datetime(start_str.strip(), errors='coerce').date()
                end_date = pd.to_datetime(end_str.strip(), errors='coerce').date()
                if start_date and end_date:
                    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
            else:
                single_date = pd.to_datetime(day.strip(), errors='coerce').date()
                if single_date:
                    date_list = [single_date]
        except:
            continue
        if not date_list:
            continue

        emp_id = int(float(row.get("Employee ID")))
        emp = Employee.query.get(emp_id)
        if not emp:
            continue

        time_in = row.get("Time In")
        time_out = row.get("Time Out")

        for att_date in date_list:
            existing = Attendance.query.filter_by(employee_id=emp.id, date=att_date).first()
            if existing:
                continue

            time_in_obj = pd.to_datetime(time_in, errors='coerce').time() if time_in else None
            time_out_obj = pd.to_datetime(time_out, errors='coerce').time() if time_out else None

            new_att = Attendance(
                employee_id=emp.id,
                date=att_date,
                time_in=time_in_obj,
                time_out=time_out_obj,
                status="Present" if time_in_obj else "Absent",
                remarks=""
            )
            db.session.add(new_att)
            imported_count += 1

    db.session.commit()
    session.pop('officer_attendance_preview', None)
    flash(f"✅ Successfully imported {imported_count} attendance record(s).", "success")
    return redirect(url_for('officer.add_bulk_attendance'))





# ------------------------- Leaves -------------------------
@hr_officer_bp.route('/leaves')
@login_required
@hr_officer_required
def view_leaves():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('hr/officer/officer_view_leaves.html', leaves=leaves, status_filter=status_filter)


# ----------------- OFFICER EDIT PASSWORD ROUTE -----------------
@hr_officer_bp.route('/edit_password', methods=['GET', 'POST'])
@login_required
@hr_officer_required
def edit_password():
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if not new_password:
            flash("⚠️ Password cannot be empty.", "warning")
            return redirect(url_for('officer.edit_password'))

        # Update password directly (or hash it if your User model supports it)
        current_user.password = new_password
        try:
            db.session.commit()
            flash("✅ Password successfully updated.", "success")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating officer password: {e}")
            flash("❌ Error updating password. Please try again.", "danger")

        return redirect(url_for('officer.edit_password'))

    # GET request → show the form
    return render_template('hr/officer/officer_edit_profile.html', user=current_user)
