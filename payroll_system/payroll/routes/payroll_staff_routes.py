from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from payroll_system.payroll.models.user import PayrollUser
from payroll_system.payroll.models.payroll_models import Employee, Payroll, Payslip, PayrollPeriod
from payroll_system.payroll.forms import PayslipForm, PayrollSummaryForm
from payroll_system.payroll.utils import staff_required, calculate_payroll_summary, get_current_payroll_period
from payroll_system.payroll import db
from datetime import datetime, date
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))  # Thesis/
TEMPLATE_DIR = os.path.join(BASE_DIR,  "templates", "payroll", "staff")
STATIC_DIR = os.path.join(BASE_DIR, "payroll_static")


payroll_staff_bp = Blueprint(
    "payroll_staff",
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/payroll/static"
)
@payroll_staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    # Get statistics
    total_employees = Employee.query.filter_by(active=True).count()
    total_payrolls = Payroll.query.count()
    total_payslips = Payslip.query.count()
    
    # Get current payroll period
    current_period = get_current_payroll_period()
    
    # Get recent payrolls
    recent_payrolls = Payroll.query.order_by(Payroll.created_at.desc()).limit(5).all()
    
    # Get recent payslips
    recent_payslips = Payslip.query.order_by(Payslip.generated_at.desc()).limit(5).all()
    
    return render_template('staff_dashboard.html',
                         total_employees=total_employees,
                         total_payrolls=total_payrolls,
                         total_payslips=total_payslips,
                         current_period=current_period,
                         recent_payrolls=recent_payrolls,
                         recent_payslips=recent_payslips)

@payroll_staff_bp.route('/employees')
@login_required
@staff_required
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
    
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    return render_template('payroll/employees.html', 
                         employees=employees, 
                         departments=departments,
                         search=search,
                         selected_department=department)

@payroll_staff_bp.route('/payroll')
@login_required
@staff_required
def payroll():
    page = request.args.get('page', 1, type=int)
    period_id = request.args.get('period', '')
    employee_id = request.args.get('employee', '')
    
    query = Payroll.query
    
    if period_id:
        query = query.filter_by(id=period_id)
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    payrolls = query.order_by(Payroll.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    periods = PayrollPeriod.query.all()
    employees = Employee.query.filter_by(active=True).all()
    
    return render_template('payroll/payroll.html', 
                         payrolls=payrolls, 
                         periods=periods,
                         employees=employees,
                         selected_period=period_id,
                         selected_employee=employee_id)

@payroll_staff_bp.route('/payslips')
@login_required
@staff_required
def payslips():
    page = request.args.get('page', 1, type=int)
    employee_id = request.args.get('employee', '')
    status = request.args.get('status', '')
    
    query = Payslip.query
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    if status:
        query = query.filter_by(status=status)
    
    payslips = query.order_by(Payslip.generated_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    employees = Employee.query.filter_by(active=True).all()
    
    return render_template('payroll/payslips.html', 
                         payslips=payslips, 
                         employees=employees,
                         selected_employee=employee_id,
                         selected_status=status)

@payroll_staff_bp.route('/payslips/generate', methods=['GET', 'POST'])
@login_required
@staff_required
def generate_payslip():
    form = PayslipForm()
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).all()]
    form.payroll_id.choices = [(p.id, f"{p.period_name} ({p.start_date} to {p.end_date})") for p in PayrollPeriod.query.all()]
    
    if form.validate_on_submit():
        # Generate payslip logic here
        flash('Payslip generated successfully!', 'success')
        return redirect(url_for('payroll_staff.payslips'))
    
    return render_template('payroll/generate_payslip.html', form=form)

@payroll_staff_bp.route('/reports')
@login_required
@staff_required
def reports():
    form = PayrollSummaryForm()
    form.period_id.choices = [(p.id, f"{p.period_name} ({p.start_date} to {p.end_date})") for p in PayrollPeriod.query.all()]
    
    summary = None
    if request.method == 'POST' and form.validate_on_submit():
        summary = calculate_payroll_summary(form.period_id.data, form.department.data)
    
    return render_template('payroll/reports.html', form=form, summary=summary)


