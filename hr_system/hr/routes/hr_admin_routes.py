from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department
from ..forms import EmployeeForm, AttendanceForm, LeaveForm, DepartmentForm
from ..utils import admin_required, generate_employee_id, get_attendance_summary, get_current_month_range
from .. import db
from datetime import timedelta
from collections import defaultdict


hr_admin_bp = Blueprint('hr_admin', __name__)

# ------------------------- Dashboard -------------------------
# ------------------------- Dashboard -------------------------
@hr_admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_employees = Employee.query.filter_by(active=True).count()
    total_users = User.query.count()
    total_departments = Department.query.count()

    recent_employees = Employee.query.order_by(Employee.created_at.desc()).limit(5).all()
    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()

    start_date, end_date = get_current_month_range()
    dates = []
    present_counts, absent_counts, late_counts = [], [], []
    
    current_date = start_date
    while current_date <= end_date:
        records = Attendance.query.filter_by(date=current_date).all()
        dates.append(current_date.strftime("%b %d"))  # e.g. Sep 01
        present_counts.append(len([r for r in records if r.status == "Present"]))
        absent_counts.append(len([r for r in records if r.status == "Absent"]))
        late_counts.append(len([r for r in records if r.status == "Late"]))
        current_date += timedelta(days=1)

    # Employees per department
    dept_data = db.session.query(
        Department.name, db.func.count(Employee.id)
    ).join(Employee, Employee.department_id == Department.id)\
     .group_by(Department.name).all()

    dept_labels = [d[0] for d in dept_data]
    dept_counts = [d[1] for d in dept_data]

    return render_template(
        'hr/admin/admin_dashboard.html',
        total_employees=total_employees,
        total_users=total_users,
        total_departments=total_departments,
        recent_employees=recent_employees,
        recent_leaves=recent_leaves,
        dates=dates,
        present_counts=present_counts,
        absent_counts=absent_counts,
        late_counts=late_counts,
        dept_labels=dept_labels,
        dept_counts=dept_counts
    )


# ------------------------- Employees -------------------------
@hr_admin_bp.route('/employees')
@login_required
@admin_required
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
        query = query.filter_by(department_id=department)

    employees = query.paginate(page=page, per_page=10, error_out=False)
    departments = Department.query.all()

    return render_template(
        'hr/admin/admin_view_employees.html',
        employees=employees,
        departments=departments,
        search=search,
        selected_department=department
    )

@hr_admin_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    form = EmployeeForm()
    if form.validate_on_submit():
        last_employee = Employee.query.filter_by(department_id=form.department.data)\
                                     .order_by(Employee.id.desc()).first()
        employee_id = generate_employee_id(form.department.data, last_employee.employee_id if last_employee else None)

        employee = Employee(
            employee_id=employee_id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            middle_name=form.middle_name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            department_id=form.department.data,
            position=form.position.data,
            salary=form.salary.data,
            date_hired=form.date_hired.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            marital_status=form.marital_status.data,
            emergency_contact=form.emergency_contact.data,
            emergency_phone=form.emergency_phone.data,
            active=form.active.data
        )

        try:
            db.session.add(employee)
            db.session.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('hr_admin.employees'))
        except Exception:
            db.session.rollback()
            flash('Error adding employee. Please try again.', 'error')

    return render_template('hr/add_employee.html', form=form)

@hr_admin_bp.route('/employees/<int:employee_id>')
@login_required
@admin_required
def view_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    return render_template('hr/admin/view_employee.html', employee=employee)

@hr_admin_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)

    if form.validate_on_submit():
        for field in ['first_name', 'last_name', 'middle_name', 'email', 'phone', 'address',
                      'department_id', 'position', 'salary', 'date_hired', 'date_of_birth',
                      'gender', 'marital_status', 'emergency_contact', 'emergency_phone', 'active']:
            setattr(employee, field, getattr(form, field).data)
        employee.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('hr_admin.view_employee', employee_id=employee.id))
        except Exception:
            db.session.rollback()
            flash('Error updating employee. Please try again.', 'error')

    return render_template('hr/edit_employee.html', form=form, employee=employee)

# ------------------------- Attendance -------------------------
@hr_admin_bp.route('/attendance')
@login_required
@admin_required
def attendance():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    employee_filter = request.args.get('employee', '')

    query = Attendance.query
    if date_filter:
        query = query.filter_by(date=datetime.strptime(date_filter, '%Y-%m-%d').date())
    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)

    attendances = query.order_by(Attendance.date.desc())\
                       .paginate(page=page, per_page=20, error_out=False)
    employees = Employee.query.filter_by(active=True).all()

    return render_template(
        'hr/attendance.html',
        attendances=attendances,
        employees=employees,
        date_filter=date_filter,
        employee_filter=employee_filter
    )

@hr_admin_bp.route('/attendance/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_attendance():
    form = AttendanceForm()
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).all()]

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
            return redirect(url_for('hr_admin.attendance'))
        except Exception:
            db.session.rollback()
            flash('Error recording attendance. Please try again.', 'error')

    return render_template('hr/add_attendance.html', form=form)

# ------------------------- Leaves -------------------------
@hr_admin_bp.route('/leaves')
@login_required
@admin_required
def leaves():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('hr/leaves.html', leaves=leaves, status_filter=status_filter)

@hr_admin_bp.route('/leaves/<int:leave_id>/approve', methods=['POST'])
@login_required
@admin_required
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

    return redirect(url_for('hr_admin.leaves'))

# ------------------------- Departments -------------------------
@hr_admin_bp.route('/departments')
@login_required
@admin_required
def departments():
    departments = Department.query.all()
    return render_template('hr/departments.html', departments=departments)

@hr_admin_bp.route('/departments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_department():
    form = DepartmentForm()
    form.head_id.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter(User.role.in_(['admin','officer','dept_head'])).all()]

    if form.validate_on_submit():
        department = Department(
            name=form.name.data,
            description=form.description.data,
            head_id=form.head_id.data if form.head_id.data else None
        )
        try:
            db.session.add(department)
            db.session.commit()
            flash('Department added successfully!', 'success')
            return redirect(url_for('hr_admin.departments'))
        except Exception:
            db.session.rollback()
            flash('Error adding department. Please try again.', 'error')

    return render_template('hr/add_department.html', form=form)

# ------------------------- Users -------------------------
@hr_admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('hr/users.html', users=users)

# ------------------------- Reports -------------------------
@hr_admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('hr/reports.html')
