from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave
from ..forms import EmployeeForm, AttendanceForm, LeaveForm
from ..utils import hr_officer_required, get_attendance_summary, get_current_month_range
from .. import db

hr_officer_bp = Blueprint('hr_officer', __name__)

# ------------------------- Dashboard -------------------------
@hr_officer_bp.route('/dashboard')
@login_required
@hr_officer_required
def dashboard():
    total_employees = Employee.query.filter_by(active=True).count()
    recent_employees = Employee.query.order_by(Employee.created_at.desc()).limit(5).all()
    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()

    start_date, end_date = get_current_month_range()
    attendance_summary = get_attendance_summary(None, start_date, end_date)

    return render_template(
        'hr/officer_dashboard.html',
        total_employees=total_employees,
        recent_employees=recent_employees,
        recent_leaves=recent_leaves,
        attendance_summary=attendance_summary
    )

# ------------------------- Employees -------------------------
@hr_officer_bp.route('/employees')
@login_required
@hr_officer_required
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    department = request.args.get('department', '')

    query = Employee.query.filter_by(active=True)
    if search:
        query = query.filter(
            (Employee.first_name.contains(search)) |
            (Employee.last_name.contains(search)) |
            (Employee.employee_id.contains(search))
        )
    if department:
        query = query.filter_by(department=department)

    employees = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'hr/employees.html',
        employees=employees,
        search=search,
        selected_department=department
    )

# ------------------------- Attendance -------------------------
@hr_officer_bp.route('/attendance')
@login_required
@hr_officer_required
def attendance():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    employee_filter = request.args.get('employee', '')

    query = Attendance.query
    if date_filter:
        query = query.filter_by(date=datetime.strptime(date_filter, '%Y-%m-%d').date())
    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)

    attendances = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=20, error_out=False)
    employees = Employee.query.filter_by(active=True).all()

    return render_template(
        'hr/attendance.html',
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
    form.employee_id.choices = [
        (e.id, f"{e.employee_id} - {e.get_full_name()}") 
        for e in Employee.query.filter_by(active=True).all()
    ]

    if form.validate_on_submit():
        attendance = Attendance(
            employee_id=form.employee_id.data,
            date=form.date.data,
            time_in=form.time_in.data,
            time_out=form.time_out.data,
            status=form.status.data,
            remarks=form.remarks.data
        )
        try:
            db.session.add(attendance)
            db.session.commit()
            flash('Attendance recorded successfully!', 'success')
            return redirect(url_for('hr_officer.attendance'))
        except Exception:
            db.session.rollback()
            flash('Error recording attendance. Please try again.', 'error')

    return render_template('hr/add_attendance.html', form=form)

# ------------------------- Leaves -------------------------
@hr_officer_bp.route('/leaves')
@login_required
@hr_officer_required
def leaves():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    return render_template('hr/leaves.html', leaves=leaves, status_filter=status_filter)

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
