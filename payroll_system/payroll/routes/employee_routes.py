from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from payroll.models.user import PayrollUser
from payroll.models.payroll_models import Employee, Payroll, Payslip
from payroll.forms import PayslipSearchForm
from payroll import db
from datetime import datetime, date

payroll_employee_bp = Blueprint('payroll_employee', __name__)

@payroll_employee_bp.route('/dashboard')
@login_required
def dashboard():
    # Get employee record
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    # Get recent payrolls
    recent_payrolls = Payroll.query.filter_by(employee_id=employee.id).order_by(Payroll.created_at.desc()).limit(5).all()
    
    # Get recent payslips
    recent_payslips = Payslip.query.filter_by(employee_id=employee.id).order_by(Payslip.generated_at.desc()).limit(5).all()
    
    # Get current month payroll
    current_month = date.today().replace(day=1)
    current_payroll = Payroll.query.filter(
        Payroll.employee_id == employee.id,
        Payroll.pay_period_start >= current_month
    ).first()
    
    return render_template('payroll/employee_dashboard.html',
                         employee=employee,
                         recent_payrolls=recent_payrolls,
                         recent_payslips=recent_payslips,
                         current_payroll=current_payroll)

@payroll_employee_bp.route('/profile')
@login_required
def profile():
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    return render_template('payroll/employee_profile.html', employee=employee)

@payroll_employee_bp.route('/payslips')
@login_required
def payslips():
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Payslip.query.filter_by(employee_id=employee.id)
    
    if status:
        query = query.filter_by(status=status)
    
    payslips = query.order_by(Payslip.generated_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('payroll/employee_payslips.html', 
                         payslips=payslips, 
                         employee=employee,
                         selected_status=status)

@payroll_employee_bp.route('/payslips/<int:payslip_id>')
@login_required
def view_payslip(payslip_id):
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=employee.id).first_or_404()
    
    return render_template('payroll/view_payslip.html', payslip=payslip, employee=employee)

@payroll_employee_bp.route('/payslips/<int:payslip_id>/download')
@login_required
def download_payslip(payslip_id):
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    payslip = Payslip.query.filter_by(id=payslip_id, employee_id=employee.id).first_or_404()
    
    # Update status to downloaded
    payslip.status = 'Downloaded'
    db.session.commit()
    
    # This would generate and return the PDF
    flash('Payslip downloaded successfully!', 'success')
    return redirect(url_for('payroll_employee.payslips'))

@payroll_employee_bp.route('/payroll-history')
@login_required
def payroll_history():
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    page = request.args.get('page', 1, type=int)
    year = request.args.get('year', date.today().year, type=int)
    
    query = Payroll.query.filter_by(employee_id=employee.id)
    
    if year:
        query = query.filter(
            Payroll.pay_period_start >= date(year, 1, 1),
            Payroll.pay_period_start <= date(year, 12, 31)
        )
    
    payrolls = query.order_by(Payroll.pay_period_start.desc()).paginate(page=page, per_page=12, error_out=False)
    
    # Get available years
    years = db.session.query(Payroll.pay_period_start).filter_by(employee_id=employee.id).all()
    years = list(set([p[0].year for p in years if p[0]]))
    years.sort(reverse=True)
    
    return render_template('payroll/employee_payroll_history.html', 
                         payrolls=payrolls, 
                         employee=employee,
                         selected_year=year,
                         years=years)

@payroll_employee_bp.route('/payroll-summary')
@login_required
def payroll_summary():
    employee = Employee.query.filter_by(email=current_user.email).first()
    
    if not employee:
        flash('Employee record not found. Please contact HR.', 'error')
        return redirect(url_for('payroll_auth.logout'))
    
    year = request.args.get('year', date.today().year, type=int)
    
    # Get payroll summary for the year
    payrolls = Payroll.query.filter(
        Payroll.employee_id == employee.id,
        Payroll.pay_period_start >= date(year, 1, 1),
        Payroll.pay_period_start <= date(year, 12, 31)
    ).all()
    
    summary = {
        'total_gross_pay': sum(p.gross_pay for p in payrolls),
        'total_deductions': sum(p.total_deductions for p in payrolls),
        'total_net_pay': sum(p.net_pay for p in payrolls),
        'total_sss': sum(p.sss_contribution for p in payrolls),
        'total_philhealth': sum(p.philhealth_contribution for p in payrolls),
        'total_pagibig': sum(p.pagibig_contribution for p in payrolls),
        'total_tax': sum(p.tax_withheld for p in payrolls),
        'payroll_count': len(payrolls)
    }
    
    # Get available years
    years = db.session.query(Payroll.pay_period_start).filter_by(employee_id=employee.id).all()
    years = list(set([p[0].year for p in years if p[0]]))
    years.sort(reverse=True)
    
    return render_template('payroll/employee_payroll_summary.html', 
                         summary=summary, 
                         employee=employee,
                         selected_year=year,
                         years=years)


