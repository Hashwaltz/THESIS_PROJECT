from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department, Position
from ..forms import EmployeeForm, AttendanceForm, LeaveForm, DepartmentForm
from ..utils import admin_required, generate_employee_id, get_attendance_summary, get_current_month_range
from .. import db
from datetime import timedelta
from sqlalchemy.orm import joinedload
from collections import defaultdict
from hr_system.hr.functions import parse_date


hr_admin_bp = Blueprint('hr_admin', __name__)

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
def view_employees():
    # Get all employees with department and position loaded in one query
    employees = Employee.query.options(
        joinedload(Employee.department),
        joinedload(Employee.position)
    ).all()

    return render_template(
        'hr/admin/admin_view_employees.html',
        employees=employees
    )


@hr_admin_bp.route('/employee/<int:employee_id>')
@login_required
@admin_required
def get_employee(employee_id):
    employee = Employee.query.options(
        joinedload(Employee.department),
        joinedload(Employee.position)
    ).filter_by(id=employee_id).first()

    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    return jsonify({
        'id': employee.id,
        'employee_id': employee.employee_id,
        'full_name': employee.get_full_name(),
        'email': employee.email,
        'phone': employee.phone,
        'department': employee.department.name if employee.department else '-',
        'position': employee.position.name if employee.position else '-',
        'date_hired': employee.date_hired.strftime('%Y-%m-%d') if employee.date_hired else '-',
        'status': 'Active' if employee.active else 'Inactive'
    })


@hr_admin_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    if request.method == 'POST':
        department_id = request.form['department']
        employee_id = generate_employee_id(department_id)

        # Safely parse dates
        date_hired = parse_date(request.form['date_hired'], "Date Hired")
        date_of_birth = parse_date(request.form['date_of_birth'], "Date of Birth")

        if not date_hired or not date_of_birth:
            return redirect(url_for('hr_admin.add_employee'))

        # --- 1. Create User first ---
        default_password = "password123"
        user = User(
            username=request.form['email'],   # use email as username
            email=request.form['email'],
            role="employee",                  # default role
            password=default_password         # no hashing since you don’t want it
        )

        db.session.add(user)
        db.session.flush()  # ensures user.id is available before commit

        # --- 2. Create Employee and link to User ---
        employee = Employee(
            employee_id=employee_id,
            user_id=user.id,   # link employee to user
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            middle_name=request.form.get('middle_name'),
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            department_id=department_id,
            position_id=request.form['position'],
            salary=request.form['salary'],
            date_hired=date_hired,
            date_of_birth=date_of_birth,
            gender=request.form['gender'],
            marital_status=request.form['marital_status'],
            emergency_contact=request.form['emergency_contact'],
            emergency_phone=request.form['emergency_phone'],
            active=True
        )

        db.session.add(employee)
        db.session.commit()

        flash("Employee and user account created successfully!", "success")
        return redirect(url_for('hr_admin.view_employees'))

    # GET request: render the form
    departments = Department.query.all()
    positions = Position.query.all()
    return render_template(
        'hr/admin/admin_add.html',
        departments=departments,
        positions=positions
    )
 
@hr_admin_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    positions = Position.query.all()
    departments = Department.query.all() 

    if request.method == "POST":
        try:
            # Explicit mapping from form fields
            employee.first_name = request.form.get("first_name")
            employee.last_name = request.form.get("last_name")
            employee.middle_name = request.form.get("middle_name")
            employee.email = request.form.get("email")
            employee.phone = request.form.get("phone")
            employee.address = request.form.get("address")
            
            # 👇 handle selects manually
            employee.department_id = request.form.get("department")
            employee.position_id = request.form.get("position")

            employee.salary = request.form.get("salary") or None
            employee.date_hired = request.form.get("date_hired") or None
            employee.date_of_birth = request.form.get("date_of_birth") or None
            employee.gender = request.form.get("gender")
            employee.marital_status = request.form.get("marital_status")
            employee.emergency_contact = request.form.get("emergency_contact")
            employee.emergency_phone = request.form.get("emergency_phone")
            employee.active = bool(request.form.get("active"))
            employee.updated_at = datetime.utcnow()

            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('hr_admin.view_employees'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {employee_id}: {e}")
            flash('Error updating employee. Please try again.', 'error')

    return render_template(
        'hr/admin/admin_edit.html',
        form=form,
        employee=employee,
        positions=positions,     # 👈 pass to template
        departments=departments  # 👈 pass to template
    )



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
