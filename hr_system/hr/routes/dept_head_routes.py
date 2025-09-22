from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department
from ..forms import AttendanceForm, LeaveForm
from ..utils import dept_head_required, get_attendance_summary, get_current_month_range,get_department_attendance_summary
from .. import db


dept_head_bp = Blueprint('dept_head', __name__)

@dept_head_bp.route('/dashboard')
@login_required
@dept_head_required
def dashboard():
    # 1. Get employees in the department
    department = Department.query.get(current_user.department_id)  # if user has dept_id
    department_employees = Employee.query.filter_by(
        department_id=current_user.department_id,
        active=True
    ).all()
    total_employees = len(department_employees)

    # 2. Get recent leave requests in department (last 5)
    recent_leaves = (
        Leave.query.join(Employee)
        .filter(Employee.department_id == current_user.department_id)
        .order_by(Leave.created_at.desc())
        .limit(5)
        .all()
    )

    # 3. Attendance summary for this month
    start_date, end_date = get_current_month_range()
    attendance_summary = get_department_attendance_summary(
        current_user.department_id,
        start_date,
        end_date
    )

    return render_template(
        'hr/head/head_dashboard.html',
        department=department,
        total_employees=total_employees,
        recent_leaves=recent_leaves,
        attendance_summary=attendance_summary
    )


@dept_head_bp.route('/employee/<int:employee_id>/edit')
@login_required
@dept_head_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    # Ensure dept head can only access employees in their department
    if employee.department_id != current_user.department_id:
        flash("Unauthorized access", "danger")
        return redirect(url_for('dept_head.employees'))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return partial template for modal
        return render_template("hr/head/head_edit.html", employee=employee)

    return render_template("hr/head/employee_detail.html", employee=employee)


@dept_head_bp.route('/employees')
@login_required
@dept_head_required
def employees():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    # Only employees in the same department as the logged-in Dept Head
    query = Employee.query.filter_by(
        department=current_user.department,
        active=True
    )

    # Apply search if given
    if search:
        query = query.filter(
            (Employee.first_name.contains(search)) |
            (Employee.last_name.contains(search)) |
            (Employee.employee_id.contains(search))
        )

    # Paginate results
    employees = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'hr/head/head_employee.html',
        employees=employees,
        search=search
    )
@dept_head_bp.route('/attendance')
@login_required
@dept_head_required
def attendance():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    employee_filter = request.args.get('employee', '')

    # Department restriction
    dept_id = current_user.department_id

    # Get employees in department
    employees = Employee.query.filter_by(department_id=dept_id).all()

    # Base query (attendance only from this department)
    query = Attendance.query.join(Employee).filter(Employee.department_id == dept_id)

    # Apply filters
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter(Attendance.date == date_obj)
        except ValueError:
            pass  # ignore invalid date

    if employee_filter:
        query = query.filter(Attendance.employee_id == int(employee_filter))

    attendances = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=10, error_out=False)

    return render_template(
        "hr/dept_head/attendance.html",
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
