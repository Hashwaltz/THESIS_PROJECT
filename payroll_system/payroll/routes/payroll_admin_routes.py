from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from payroll.models.user import PayrollUser
from payroll.models.payroll_models import Employee, Payroll, Payslip, PayrollPeriod, Deduction, Allowance, Tax
from payroll.forms import PayrollPeriodForm, PayrollForm, PayslipForm, DeductionForm, AllowanceForm, TaxForm, PayrollSummaryForm
from payroll.utils import admin_required, calculate_payroll_summary, get_current_payroll_period, create_payroll_period, process_payroll_for_employee, sync_all_employees_from_hr
from payroll import db
from datetime import datetime, date

payroll_admin_bp = Blueprint('payroll_admin', __name__)

@payroll_admin_bp.route('/dashboard')
@login_required
@admin_required
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
    
    return render_template('payroll/admin_dashboard.html',
                         total_employees=total_employees,
                         total_payrolls=total_payrolls,
                         total_payslips=total_payslips,
                         current_period=current_period,
                         recent_payrolls=recent_payrolls,
                         recent_payslips=recent_payslips)

@payroll_admin_bp.route('/employees')
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
        query = query.filter_by(department=department)
    
    employees = query.paginate(page=page, per_page=10, error_out=False)
    
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments if dept[0]]
    
    return render_template('payroll/employees.html', 
                         employees=employees, 
                         departments=departments,
                         search=search,
                         selected_department=department)

@payroll_admin_bp.route('/employees/sync', methods=['POST'])
@login_required
@admin_required
def sync_employees():
    """Sync employees from HR system"""
    try:
        hr_employees = sync_all_employees_from_hr()
        
        if not hr_employees:
            flash('No employees found in HR system or sync failed.', 'error')
            return redirect(url_for('payroll_admin.employees'))
        
        synced_count = 0
        for emp_data in hr_employees:
            # Check if employee already exists
            existing_employee = Employee.query.filter_by(employee_id=emp_data['employee_id']).first()
            
            if not existing_employee:
                employee = Employee(
                    employee_id=emp_data['employee_id'],
                    first_name=emp_data['first_name'],
                    last_name=emp_data['last_name'],
                    middle_name=emp_data.get('middle_name'),
                    email=emp_data['email'],
                    phone=emp_data.get('phone'),
                    department=emp_data['department'],
                    position=emp_data['position'],
                    basic_salary=emp_data.get('salary', 0),
                    date_hired=datetime.strptime(emp_data['date_hired'], '%Y-%m-%d').date() if emp_data.get('date_hired') else date.today(),
                    active=emp_data.get('active', True)
                )
                db.session.add(employee)
                synced_count += 1
            else:
                # Update existing employee
                existing_employee.first_name = emp_data['first_name']
                existing_employee.last_name = emp_data['last_name']
                existing_employee.middle_name = emp_data.get('middle_name')
                existing_employee.email = emp_data['email']
                existing_employee.phone = emp_data.get('phone')
                existing_employee.department = emp_data['department']
                existing_employee.position = emp_data['position']
                existing_employee.basic_salary = emp_data.get('salary', 0)
                existing_employee.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Successfully synced {synced_count} employees from HR system.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error syncing employees. Please try again.', 'error')
    
    return redirect(url_for('payroll_admin.employees'))

@payroll_admin_bp.route('/payroll-periods')
@login_required
@admin_required
def payroll_periods():
    periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()
    return render_template('payroll/payroll_periods.html', periods=periods)

@payroll_admin_bp.route('/payroll-periods/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_payroll_period():
    form = PayrollPeriodForm()
    
    if form.validate_on_submit():
        period = create_payroll_period(
            form.period_name.data,
            form.start_date.data,
            form.end_date.data,
            form.pay_date.data
        )
        
        if period:
            flash('Payroll period created successfully!', 'success')
            return redirect(url_for('payroll_admin.payroll_periods'))
        else:
            flash('Error creating payroll period. Please try again.', 'error')
    
    return render_template('payroll/add_payroll_period.html', form=form)

@payroll_admin_bp.route('/payroll')
@login_required
@admin_required
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

@payroll_admin_bp.route('/payroll/process', methods=['POST'])
@login_required
@admin_required
def process_payroll():
    """Process payroll for all employees in current period"""
    try:
        current_period = get_current_payroll_period()
        
        if not current_period:
            flash('No active payroll period found.', 'error')
            return redirect(url_for('payroll_admin.payroll'))
        
        employees = Employee.query.filter_by(active=True).all()
        processed_count = 0
        
        for employee in employees:
            # Check if payroll already exists for this employee and period
            existing_payroll = Payroll.query.filter_by(
                employee_id=employee.id,
                pay_period_start=current_period.start_date,
                pay_period_end=current_period.end_date
            ).first()
            
            if not existing_payroll:
                payroll = process_payroll_for_employee(employee.id, current_period.id)
                if payroll:
                    processed_count += 1
        
        flash(f'Successfully processed payroll for {processed_count} employees.', 'success')
        
    except Exception as e:
        flash('Error processing payroll. Please try again.', 'error')
    
    return redirect(url_for('payroll_admin.payroll'))

@payroll_admin_bp.route('/payslips')
@login_required
@admin_required
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

@payroll_admin_bp.route('/payslips/generate', methods=['GET', 'POST'])
@login_required
@admin_required
def generate_payslip():
    form = PayslipForm()
    form.employee_id.choices = [(e.id, f"{e.employee_id} - {e.get_full_name()}") for e in Employee.query.filter_by(active=True).all()]
    form.payroll_id.choices = [(p.id, f"{p.period_name} ({p.start_date} to {p.end_date})") for p in PayrollPeriod.query.all()]
    
    if form.validate_on_submit():
        # Generate payslip logic here
        flash('Payslip generated successfully!', 'success')
        return redirect(url_for('payroll_admin.payslips'))
    
    return render_template('payroll/generate_payslip.html', form=form)

@payroll_admin_bp.route('/deductions')
@login_required
@admin_required
def deductions():
    deductions = Deduction.query.all()
    return render_template('payroll/deductions.html', deductions=deductions)

@payroll_admin_bp.route('/deductions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_deduction():
    form = DeductionForm()
    
    if form.validate_on_submit():
        deduction = Deduction(
            name=form.name.data,
            description=form.description.data,
            type=form.type.data,
            amount=form.amount.data,
            percentage=form.percentage.data,
            is_mandatory=form.is_mandatory.data,
            active=form.active.data
        )
        
        try:
            db.session.add(deduction)
            db.session.commit()
            flash('Deduction added successfully!', 'success')
            return redirect(url_for('payroll_admin.deductions'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding deduction. Please try again.', 'error')
    
    return render_template('payroll/add_deduction.html', form=form)

@payroll_admin_bp.route('/allowances')
@login_required
@admin_required
def allowances():
    allowances = Allowance.query.all()
    return render_template('payroll/allowances.html', allowances=allowances)

@payroll_admin_bp.route('/allowances/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_allowance():
    form = AllowanceForm()
    
    if form.validate_on_submit():
        allowance = Allowance(
            name=form.name.data,
            description=form.description.data,
            type=form.type.data,
            amount=form.amount.data,
            percentage=form.percentage.data,
            active=form.active.data
        )
        
        try:
            db.session.add(allowance)
            db.session.commit()
            flash('Allowance added successfully!', 'success')
            return redirect(url_for('payroll_admin.allowances'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding allowance. Please try again.', 'error')
    
    return render_template('payroll/add_allowance.html', form=form)

@payroll_admin_bp.route('/tax-brackets')
@login_required
@admin_required
def tax_brackets():
    tax_brackets = Tax.query.order_by(Tax.min_income).all()
    return render_template('payroll/tax_brackets.html', tax_brackets=tax_brackets)

@payroll_admin_bp.route('/tax-brackets/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_tax_bracket():
    form = TaxForm()
    
    if form.validate_on_submit():
        tax_bracket = Tax(
            min_income=form.min_income.data,
            max_income=form.max_income.data,
            tax_rate=form.tax_rate.data,
            fixed_amount=form.fixed_amount.data,
            active=form.active.data
        )
        
        try:
            db.session.add(tax_bracket)
            db.session.commit()
            flash('Tax bracket added successfully!', 'success')
            return redirect(url_for('payroll_admin.tax_brackets'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding tax bracket. Please try again.', 'error')
    
    return render_template('payroll/add_tax_bracket.html', form=form)

@payroll_admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    form = PayrollSummaryForm()
    form.period_id.choices = [(p.id, f"{p.period_name} ({p.start_date} to {p.end_date})") for p in PayrollPeriod.query.all()]
    
    summary = None
    if request.method == 'POST' and form.validate_on_submit():
        summary = calculate_payroll_summary(form.period_id.data, form.department.data)
    
    return render_template('payroll/reports.html', form=form, summary=summary)


