from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department
from ..forms import EmployeeForm, AttendanceForm, LeaveForm
from ..utils import hr_officer_required, get_attendance_summary, get_current_month_range
from .. import db
from sqlalchemy.orm import joinedload


hr_officer_bp = Blueprint('hr_officer', __name__,
                           template_folder='../templates',
                           static_folder='../static')


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
    employee = Employee.query.get_or_404(employee_id)

    if request.method == "POST":
        try:
            
            employee.phone = request.form.get("phone")
            employee.address = request.form.get("address")
            employee.marital_status = request.form.get("marital_status")
            employee.emergency_contact = request.form.get("emergency_contact")
            employee.emergency_phone = request.form.get("emergency_phone")

            # System fields
            employee.updated_at = datetime.utcnow()

            db.session.commit()
            flash("Employee contact details updated successfully!", "success")
            return redirect(url_for("hr_officer.employees"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {employee_id}: {e}")
            flash("Error updating employee. Please try again.", "error")

    # 🔹 Render the HR Officer template (limited fields only)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "hr/officer/officer_edit.html",
            employee=employee
        )

    return render_template(
        "hr/officer/officer_edit.html",
        employee=employee
    )




# Your existing view_attendance route for officer
@hr_officer_bp.route('/attendance')
@login_required
@hr_officer_required
def attendance():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    employee_filter = request.args.get('employee', '')

    query = Attendance.query.options(joinedload(Attendance.employee))
    if date_filter:
        try:
            query = query.filter_by(date=datetime.strptime(date_filter, '%Y-%m-%d').date())
        except ValueError:
            flash('Invalid date format.', 'danger')
            date_filter = '' # Clear invalid filter
            return redirect(url_for('hr_officer.attendance', employee=employee_filter))

    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)

    attendances = query.order_by(Attendance.date.desc(), Attendance.time_in.desc())\
                       .paginate(page=page, per_page=10, error_out=False) # Reduced per_page for testing
    employees = Employee.query.filter_by(active=True).order_by(Employee.first_name).all()

    return render_template(
        'hr/officer/officer_view_attend.html',
        attendances=attendances,
        employees=employees,
        date_filter=date_filter,
        employee_filter=employee_filter
    )

@hr_officer_bp.route('/attendance/add', methods=['GET', 'POST'])
@login_required
@hr_officer_required
def add_attendance():
    form = AttendanceForm()
    # Populate choices for employee_id
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).order_by(Employee.first_name).all()]

    if form.validate_on_submit():
        try:
            # Check for existing attendance for the same employee and date
            existing_attendance = Attendance.query.filter_by(
                employee_id=form.employee_id.data,
                date=form.date.data
            ).first()

            if existing_attendance:
                flash('Attendance record for this employee and date already exists. Please use "Edit" to modify.', 'warning')
                return redirect(url_for('hr_officer.add_attendance'))

            attendance = Attendance(
                employee_id=form.employee_id.data,
                date=form.date.data,
                time_in=form.time_in.data,
                time_out=form.time_out.data,
                status=form.status.data,
                remarks=form.remarks.data
            )
            db.session.add(attendance)
            db.session.commit()
            flash('Attendance recorded successfully!', 'success')
            return redirect(url_for('hr_officer.attendance'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding attendance: {e}")
            flash('Error recording attendance. Please try again.', 'error')

    return render_template('hr/officer/officer_add_attendance.html', form=form, title="Mark New Attendance")



# --- EDIT ATTENDANCE ---
@hr_officer_bp.route('/attendance/<int:attendance_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_officer_required
def edit_attendance(attendance_id):
    attendance_record = Attendance.query.get_or_404(attendance_id)
    form = AttendanceForm(obj=attendance_record) 
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).order_by(Employee.first_name).all()]

    if form.validate_on_submit():
        try:
            attendance_record.employee_id = form.employee_id.data
            attendance_record.date = form.date.data
            attendance_record.time_in = form.time_in.data
            attendance_record.time_out = form.time_out.data
            attendance_record.status = form.status.data
            attendance_record.remarks = form.remarks.data
            attendance_record.updated_at = datetime.utcnow() 

            db.session.commit()
            flash('Attendance record updated successfully!', 'success')
            return redirect(url_for('hr_officer.attendance'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating attendance record {attendance_id}: {e}")
            flash('Error updating attendance record. Please try again.', 'error')

    return render_template(
        'hr/officer/officer_add_attendance.html', 
        form=form,
        title="Edit Attendance Record",
        attendance_record=attendance_record 
    )

# --- DELETE ATTENDANCE ---
@hr_officer_bp.route('/attendance/<int:attendance_id>/delete', methods=['POST'])
@login_required
@hr_officer_required
def delete_attendance(attendance_id):
    attendance_record = Attendance.query.get_or_404(attendance_id)
    try:
        db.session.delete(attendance_record)
        db.session.commit()
        flash('Attendance record deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting attendance record {attendance_id}: {e}")
        flash('Error deleting attendance record. Please try again.', 'error')
    return redirect(url_for('hr_officer.attendance'))



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


@hr_officer_bp.route('/leaves/<int:leave_id>/approve', methods=['POST'])
@login_required
@hr_officer_required
def approve_leave(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    leave.status = request.form.get('status')
    leave.comments = request.form.get('comments', '')
    leave.approved_by = current_user.id
    leave.approved_at = datetime.utcnow()

    try:
        db.session.commit()
        flash(f'Leave request {leave.status.lower()} successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Error updating leave request.', 'error')

    return redirect(url_for('hr_officer.leaves'))
