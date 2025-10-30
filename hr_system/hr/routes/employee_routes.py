from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user, login_user
from datetime import datetime, date
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave, LeaveType
from ..forms import LeaveForm
from ..utils import get_attendance_summary, get_leave_balance, get_current_month_range, employee_required, get_attendance_chart_data
from .. import db
import os



BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "hr_static")

employee_bp = Blueprint(
    'employee',
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/hr/static'
    )

# ---------------- DASHBOARD ----------------
@employee_bp.route('/dashboard')
@login_required
@employee_required
def dashboard():
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    start_date, end_date = get_current_month_range()
    attendance_summary_totals = get_attendance_summary(employee.id, start_date, end_date)
    attendance_summary_chart = get_attendance_chart_data(employee.id, start_date, end_date)
    recent_leaves = Leave.query.filter_by(employee_id=employee.id)\
                               .order_by(Leave.created_at.desc()).limit(5).all()
    leave_balances = {lt: get_leave_balance(employee.id, lt) for lt in 
                      ['Sick', 'Vacation', 'Personal', 'Emergency', 'Maternity', 'Paternity']}

    return render_template(
        'hr/employee/employee_dashboard.html',
        employee=employee,
        attendance_summary=attendance_summary_totals,
        attendance_chart=attendance_summary_chart,
        recent_leaves=recent_leaves,
        leave_balances=leave_balances
    )

# ---------------- ATTENDANCE ----------------
@employee_bp.route('/attendance')
@login_required
@employee_required
def attendance():
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    page = request.args.get('page', 1, type=int)
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    status_filter = request.args.get('status_filter', '')

    query = Attendance.query.filter_by(employee_id=employee.id)

    # Apply date filters
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(Attendance.date >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(Attendance.date <= end_date)
    except ValueError:
        flash('Invalid date format. Use YYYY-MM-DD.', 'error')

    # Apply status filter
    if status_filter:
        query = query.filter_by(status=status_filter)

    attendances = query.order_by(Attendance.date.desc())\
                       .paginate(page=page, per_page=20, error_out=False)

    summary = {
        'present': sum(1 for a in attendances.items if a.status == 'Present'),
        'absent': sum(1 for a in attendances.items if a.status == 'Absent'),
        'late': sum(1 for a in attendances.items if a.status == 'Late'),
        'half_day': sum(1 for a in attendances.items if a.status == 'Half Day')
    }

    return render_template(
        'hr/employee/employee_attendance.html',
        attendances=attendances,
        employee=employee,
        start_date_filter=start_date_str,
        end_date_filter=end_date_str,
        status_filter=status_filter,
        summary=summary
    )


# ---------------- LEAVES ----------------
@employee_bp.route('/leaves')
@login_required
@employee_required
def leaves():
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query.filter_by(employee_id=employee.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    leave_balances = {lt: get_leave_balance(employee.id, lt) for lt in
                      ['Sick', 'Vacation', 'Personal', 'Emergency', 'Maternity', 'Paternity']}

    return render_template(
        'hr/employee/employee_leaves.html',
        leaves=leaves,
        employee=employee,
        leave_balances=leave_balances,
        status_filter=status_filter
    )


# ---------------- REQUEST LEAVE ----------------
@employee_bp.route('/employee/request_leave', methods=['GET', 'POST'])
@login_required
@employee_required
def request_leave():
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    if request.method == 'POST':
        leave_type_id = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        days_requested = (end_date_obj - start_date_obj).days + 1

        leave = Leave(
            employee_id=employee.id,
            leave_type_id=leave_type_id,
            start_date=start_date_obj,
            end_date=end_date_obj,
            days_requested=days_requested,
            reason=reason,
            status="Pending"
        )
        db.session.add(leave)
        db.session.commit()
        flash("Leave request submitted successfully!", "success")
        return redirect(url_for('employee.leaves'))

    leave_types = LeaveType.query.all()
    return render_template('hr/employee/request_leave.html', leave_types=leave_types)


# ---------------- VIEW LEAVE ----------------
@employee_bp.route('/leaves/<int:leave_id>')
@login_required
@employee_required
def view_leave(leave_id):
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    leave = Leave.query.filter_by(id=leave_id, employee_id=employee.id).first_or_404()
    return render_template('hr/employee/view_leave.html', leave=leave, employee=employee)


# ---------------- PAYSLIPS ----------------
@employee_bp.route('/payslips')
@login_required
@employee_required
def payslips():
    employee = current_user.employee_profile
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('hr_auth.logout'))

    return render_template('hr/employee_payslips.html', employee=employee)


# ----------------- EDIT PASSWORD ROUTE FOR EMPLOYEE -----------------
@employee_bp.route('/edit_password', methods=['GET', 'POST'])
@login_required
@employee_required
def edit_password():
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        if not new_password:
            flash("⚠️ Password cannot be empty.", "warning")
            return redirect(url_for('employee.edit_password'))

        # Update password directly (no hashing)
        current_user.password = new_password
        db.session.commit()

        flash("✅ Password successfully updated.", "success")
        return redirect(url_for('employee.edit_password'))

    # GET request → show the form
    return render_template('hr/employee/employee_profile.html')  # create this template
