from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave
from ..forms import AttendanceForm, LeaveForm
from ..utils import dept_head_required, get_attendance_summary, get_current_month_range
from .. import db

dept_head_bp = Blueprint('dept_head', __name__)

@dept_head_bp.route('/dashboard')
@login_required
@dept_head_required
def dashboard():
    # Employees in the current user's department
    department_employees = Employee.query.filter_by(
        department=current_user.department,
        active=True
    ).all()
    
    total_employees = len(department_employees)
    
    # Recent leaves for department
    recent_leaves = Leave.query.join(Employee).filter(
        Employee.department == current_user.department
    ).order_by(Leave.created_at.desc()).limit(5).all()
    
    # Attendance summary for current month
    start_date, end_date = get_current_month_range()
    attendance_summary = get_attendance_summary(None, start_date, end_date)
    
    return render_template(
        'hr/dept_head_dashboard.html',
        total_employees=total_employees,
        department_employees=department_employees,
        recent_leaves=recent_leaves,
        attendance_summary=attendance_summary
    )

@dept_head_bp.route('/employees')
@login_required
@dept_head_required
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = Employee.query.filter_by(
        department=current_user.department,
        active=True
    )

    if search:
        query = query.filter(
            (Employee.first_name.contains(search)) |
            (Employee.last_name.contains(search)) |
            (Employee.employee_id.contains(search))
        )

    employees = query.paginate(page=page, per_page=10, error_out=False)

    return render_template('hr/employees.html', employees=employees, search=search)

@dept_head_bp.route('/attendance')
@login_required
@dept_head_required
def attendance():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    employee_filter = request.args.get('employee', '')

    department_employee_ids = [
        e.id for e in Employee.query.filter_by(
            department=current_user.department,
            active=True
        ).all()
    ]

    query = Attendance.query.filter(Attendance.employee_id.in_(department_employee_ids))

    if date_filter:
        query = query.filter_by(date=datetime.strptime(date_filter, '%Y-%m-%d').date())
    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)

    attendances = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=20, error_out=False)
    employees = Employee.query.filter_by(department=current_user.department, active=True).all()

    return render_template(
        'hr/attendance.html',
        attendances=attendances,
        employees=employees,
        date_filter=date_filter,
        employee_filter=employee_filter
    )

@dept_head_bp.route('/attendance/add', methods=['GET', 'POST'])
@login_required
@dept_head_required
def add_attendance():
    form = AttendanceForm()
    form.employee_id.choices = [
        (e.id, f"{e.employee_id} - {e.get_full_name()}")
        for e in Employee.query.filter_by(
            department=current_user.department,
            active=True
        ).all()
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
            return redirect(url_for('dept_head.attendance'))
        except Exception:
            db.session.rollback()
            flash('Error recording attendance. Please try again.', 'error')

    return render_template('hr/add_attendance.html', form=form)

@dept_head_bp.route('/leaves')
@login_required
@dept_head_required
def leaves():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    department_employee_ids = [
        e.id for e in Employee.query.filter_by(
            department=current_user.department,
            active=True
        ).all()
    ]

    query = Leave.query.filter(Leave.employee_id.in_(department_employee_ids))

    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('hr/leaves.html', leaves=leaves, status_filter=status_filter)

@dept_head_bp.route('/leaves/<int:leave_id>/approve', methods=['POST'])
@login_required
@dept_head_required
def approve_leave(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    employee = Employee.query.get(leave.employee_id)

    if employee.department != current_user.department:
        flash('You are not authorized to approve this leave request.', 'error')
        return redirect(url_for('dept_head.leaves'))

    status = request.form.get('status')
    comments = request.form.get('comments', '')

    leave.status = status
    leave.approved_by = current_user.id
    leave.approved_at = datetime.utcnow()
    leave.comments = comments

    try:
        db.session.commit()
        flash(f'Leave request {status.lower()} successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('Error updating leave request.', 'error')

    return redirect(url_for('dept_head.leaves'))
