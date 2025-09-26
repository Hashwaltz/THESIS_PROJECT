from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from ..models.user import User
from ..models.hr_models import Employee, Attendance, Leave
from ..forms import LeaveForm
from ..utils import get_attendance_summary, get_leave_balance, get_current_month_range, employee_required, get_attendance_chart_data
from .. import db

employee_bp = Blueprint('employee', __name__,
    template_folder='../templates',
    static_folder='../static')

@employee_bp.route('/dashboard')
@login_required
@employee_required
def dashboard():
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    start_date, end_date = get_current_month_range()
    
    # For totals summary (like your info boxes)
    attendance_summary_totals = get_attendance_summary(employee.id, start_date, end_date)
    
    # For chart
    attendance_summary_chart = get_attendance_chart_data(employee.id, start_date, end_date)

    recent_leaves = Leave.query.filter_by(employee_id=employee.id)\
                               .order_by(Leave.created_at.desc()).limit(5).all()

    leave_balances = {lt: get_leave_balance(employee.id, lt) for lt in 
                      ['Sick', 'Vacation', 'Personal', 'Emergency', 'Maternity', 'Paternity']}

    return render_template(
        'hr/employee/employee_dashboard.html',
        employee=employee,
        attendance_summary=attendance_summary_totals,
        recent_leaves=recent_leaves,
        leave_balances=leave_balances,
        attendance_chart=attendance_summary_chart  # pass chart data separately
    )

@employee_bp.route('/profile')
@login_required
@employee_required
def profile():
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    return render_template('hr/employee_profile.html', employee=employee)

@employee_bp.route('/attendance')
@login_required
@employee_required
def attendance():
    # Get the employee record
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    # Pagination and filtering
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')

    query = Attendance.query.filter_by(employee_id=employee.id)
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=filter_date)
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')

    attendances = query.order_by(Attendance.date.desc())\
                       .paginate(page=page, per_page=20, error_out=False)

    # Optional: summarize attendance for display
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
        date_filter=date_filter,
        summary=summary
    )




@employee_bp.route('/leaves')
@login_required
@employee_required
def leaves():
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Leave.query.filter_by(employee_id=employee.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    leave_balances = {lt: get_leave_balance(employee.id, lt) for lt in
                      ['Sick', 'Vacation', 'Personal', 'Emergency', 'Maternity', 'Paternity']}

    return render_template('hr/employee_leaves.html',
                           leaves=leaves,
                           employee=employee,
                           leave_balances=leave_balances,
                           status_filter=status_filter)

@employee_bp.route('/leaves/request', methods=['GET', 'POST'])
@login_required
@employee_required
def request_leave():
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    form = LeaveForm()
    form.employee_id.data = employee.id

    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        days_requested = (end_date - start_date).days + 1

        if start_date < date.today():
            flash('Start date cannot be in the past.', 'error')
            return render_template('hr/request_leave.html', form=form, employee=employee)
        if end_date < start_date:
            flash('End date cannot be before start date.', 'error')
            return render_template('hr/request_leave.html', form=form, employee=employee)

        leave_balance = get_leave_balance(employee.id, form.leave_type.data)
        if days_requested > leave_balance:
            flash(f'Insufficient leave balance. Available: {leave_balance} days', 'error')
            return render_template('hr/request_leave.html', form=form, employee=employee)

        leave = Leave(
            employee_id=employee.id,
            leave_type=form.leave_type.data,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=form.reason.data
        )

        try:
            db.session.add(leave)
            db.session.commit()
            flash('Leave request submitted successfully!', 'success')
            return redirect(url_for('employee.leaves'))
        except Exception:
            db.session.rollback()
            flash('Error submitting leave request. Please try again.', 'error')

    return render_template('hr/request_leave.html', form=form, employee=employee)

@employee_bp.route('/leaves/<int:leave_id>')
@login_required
@employee_required
def view_leave(leave_id):
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    leave = Leave.query.filter_by(id=leave_id, employee_id=employee.id).first_or_404()
    return render_template('hr/view_leave.html', leave=leave, employee=employee)

@employee_bp.route('/payslips')
@login_required
def payslips():
    employee = Employee.query.filter_by(email=current_user.email).first()
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('auth.logout'))

    # Placeholder for payroll integration
    return render_template('hr/employee_payslips.html', employee=employee)
