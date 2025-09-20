from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, Department, Position
from ..forms import EmployeeForm, AttendanceForm, LeaveForm, DepartmentForm
from ..utils import admin_required, generate_employee_id, get_attendance_summary, get_current_month_range
from .. import db
from datetime import timedelta, datetime
from sqlalchemy.orm import joinedload
from collections import defaultdict
from hr_system.hr.functions import parse_date



hr_admin_bp = Blueprint('hr_admin', __name__)


# ------------------------- Dashboard -------------------------
@hr_admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = datetime.now().date()
    total_employees = Employee.query.count()
    total_users = User.query.filter_by(active=True).count()
    total_inactive = User.query.filter_by(active=False).count()
    total_departments = Department.query.count()

    recent_employees = Employee.query.order_by(Employee.created_at.desc()).limit(5).all()
    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()

   
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
        monthly_dates=monthly_dates,
        monthly_present_counts=monthly_present_counts,
        monthly_absent_counts=monthly_absent_counts,
        monthly_late_counts=monthly_late_counts,
        dept_labels=dept_labels,
        dept_counts=dept_counts,
        total_inactive=total_inactive
    )


# ------------------------- Employees -------------------------
@hr_admin_bp.route('/employees')
@login_required
@admin_required
def view_employees():
    # Get current page from query params (default to 1)
    page = request.args.get('page', 1, type=int)

    # Paginate employees with department and position
    employees = Employee.query.options(
        joinedload(Employee.department),
        joinedload(Employee.position)
    ).paginate(page=page, per_page=10)  # adjust per_page as needed

    return render_template(
        'hr/admin/admin_view_employees.html',
        employees=employees
    )
    

@hr_admin_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_employee():
    if request.method == 'POST':
        department_id = request.form['department']
        new_employee_id = generate_employee_id(department_id)
        # Safely parse dates
        date_hired = parse_date(request.form['date_hired'], "Date Hired")
        date_of_birth = parse_date(request.form['date_of_birth'], "Date of Birth")

        if not date_hired or not date_of_birth:
            return redirect(url_for('hr_admin.add_employee'))

        # --- 1. Create User first ---
        default_password = "password123"
        user = User(
            email=request.form['email'],
            first_name=request.form['first_name'],   
            last_name=request.form['last_name'],  
            role="employee",
            password=default_password
        )


        db.session.add(user)
        db.session.flush()  # ensures user.id is available before commit

        # --- 2. Create Employee and link to User ---
        employee = Employee(
            employee_id=new_employee_id,
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


@hr_admin_bp.route("/employees/<int:employee_id>/edit", methods=["GET","POST"])
@login_required
@admin_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    positions = Position.query.all()
    departments = Department.query.all()

    if request.method == "POST":
        try:
            # Explicit mapping from request.form
            employee.first_name = request.form.get("first_name")
            employee.last_name = request.form.get("last_name")
            employee.middle_name = request.form.get("middle_name")
            employee.email = request.form.get("email")
            employee.phone = request.form.get("phone")
            employee.address = request.form.get("address")

            # Foreign Keys
            dept_id = request.form.get("department")
            pos_id = request.form.get("position")
            employee.department_id = int(dept_id) if dept_id else None
            employee.position_id = int(pos_id) if pos_id else None

            # Salary
            salary_val = request.form.get("salary")
            employee.salary = float(salary_val) if salary_val else None

            # Dates
            date_hired_str = request.form.get("date_hired")
            dob_str = request.form.get("date_of_birth")
            employee.date_hired = datetime.strptime(date_hired_str, "%Y-%m-%d").date() if date_hired_str else None
            employee.date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None

            # Other fields
            employee.gender = request.form.get("gender")
            employee.marital_status = request.form.get("marital_status")
            employee.emergency_contact = request.form.get("emergency_contact")
            employee.emergency_phone = request.form.get("emergency_phone")
            active = request.form.get("status")
            employee.active = bool(active)
            employee.updated_at = datetime.utcnow()
            

            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('hr_admin.view_employees'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {employee_id}: {e}")
            flash('Error updating employee. Please try again.', 'error')

    # 🔹 If request is AJAX, only return the form partial (used in modal)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "hr/admin/admin_edit.html",
            employee=employee,
            positions=positions,
            departments=departments
        )

    # 🔹 Otherwise return full page
    return render_template(
        "hr/admin/admin_edit.html",
        employee=employee,
        positions=positions,
        departments=departments
    )



# ------------------------- Users -------------------------
@hr_admin_bp.route('/users')
@login_required
@admin_required
def view_users():
    # Get current page from query params (default to 1)
    page = request.args.get('page', 1, type=int)

    # Paginate users
    users = User.query.paginate(page=page, per_page=10)  # adjust per_page if needed
    
    department = Department.query.all()
    return render_template(
        'hr/admin/admin_view_users.html',
        users=users,
        department=department
    )



@hr_admin_bp.route("/user/<int:user_id>/edit", methods=["GET","POST"])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    positions = Position.query.all()
    departments = Department.query.all()

    if request.method == "POST":
        try:
            # Explicit mapping from request.form
            user.email = request.form.get("email")
            user.first_name = request.form.get("first_name")
            user.last_name = request.form.get("last_name")
            user.role = request.form.get("role")
            active = request.form.get("status")
            user.active = bool(active)
        

            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('hr_admin.view_users'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {user_id}: {e}")
            flash('Error updating user. Please try again.', 'error')

    # 🔹 If request is AJAX, only return the form partial (used in modal)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "hr/admin/edit_user.html",
            user=user,
            positions=positions,
            departments=departments
        )

    # 🔹 Otherwise return full page
    return render_template(
        "hr/admin/edit_user.html",
        user=user,
        positions=positions,
        departments=departments
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
        'hr/admin/admin_view_attendance.html',
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



@hr_admin_bp.route('/attendance/<int:attendance_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required # Adjust as needed (e.g., @officer_required)
def edit_attendance(attendance_id):
    attendance_record = Attendance.query.get_or_404(attendance_id)
    form = AttendanceForm(obj=attendance_record)
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).all()]

    if form.validate_on_submit():
        try:
            form.populate_obj(attendance_record) # Populates the object with form data
            attendance_record.updated_at = datetime.utcnow() # Add an update timestamp if you have one
            db.session.commit()
            flash('Attendance record updated successfully!', 'success')
            return redirect(url_for('hr_admin.attendance')) # Redirect to the main attendance view
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating attendance record {attendance_id}: {e}")
            flash('Error updating attendance record. Please try again.', 'error')
    
    # If it's a GET request or form validation failed
    return render_template('hr/admin/admin_edit_attendance.html', form=form, attendance_record=attendance_record)


@hr_admin_bp.route('/attendance/<int:attendance_id>/delete', methods=['POST'])
@login_required
@admin_required # Adjust as needed (e.g., @officer_required)
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

    return redirect(url_for('hr_admin.attendance'))


# ------------------------- Leaves -------------------------
@hr_admin_bp.route('/leaves')
@login_required
@admin_required
def view_leaves():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('hr/admin/admin_view_leaves.html', leaves=leaves, status_filter=status_filter)



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
def view_departments():
    page = request.args.get('page', 1, type=int)
    departments = Department.query.paginate(page=page, per_page=10)
    

    return render_template(
        'hr/admin/admin_view_departments.html',
        departments=departments
    )



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

    return render_template('hr/admin/admin_add_dept.html', form=form)




@hr_admin_bp.route("/department/<int:department_id>/edit", methods=["GET","POST"])
@login_required
@admin_required
def edit_department(department_id):
    department = Department.query.get_or_404(department_id)
    employees = Employee.query.filter_by(department_id=department_id).all()
    

    if request.method == "POST":
        try:
            # Explicit mapping from request.form
            department.name = request.form.get("name") or department.name
            head_id = request.form.get("dept_head")
            department.head_id = int(head_id) if head_id else department.head_id
            department.description = request.form.get("description") or department.description

            db.session.commit()
            flash('Department updated successfully!', 'success')
            return redirect(url_for('hr_admin.view_departments'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating employee {department_id}: {e}")
            flash('Error updating department. Please try again.', 'error')

    # 🔹 If request is AJAX, only return the form partial (used in modal)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "hr/admin/edit_dept.html",
            department=department, 
            employees=employees
        )

    # 🔹 Otherwise return full page
    return render_template(
        "hr/admin/edit_dept.html",
        department=department,
        employees=employees
    )







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
