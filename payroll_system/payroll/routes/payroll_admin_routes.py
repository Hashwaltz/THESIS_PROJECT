from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from payroll_system.payroll.models.user import PayrollUser
from g4f.client import Client
from payroll_system.payroll.models.payroll_models import (
    Employee, Payroll, Payslip, PayrollPeriod, Deduction, Allowance, Tax, EmployeeDeduction, EmployeeAllowance
)
from payroll_system.payroll.forms import (
    PayrollPeriodForm, PayrollForm, PayslipForm,
    DeductionForm, AllowanceForm, TaxForm, PayrollSummaryForm
)
from payroll_system.payroll.utils import (
    admin_required, calculate_payroll_summary, get_current_payroll_period,
    get_payroll_summary,generate_ai_report, generate_department_chart,
    create_payroll_period, generate_payroll_insights, sync_all_employees_from_hr
)
from payroll_system.payroll import db
from hr_system.hr.models.user import User
from hr_system.hr.models.hr_models import Department, Employee as HREmployee, Attendance
from datetime import datetime, date, timedelta, time
import os
from reportlab.lib.pagesizes import A4
from sqlalchemy import func, case, extract
from sqlalchemy.orm import joinedload
from io import BytesIO
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "payroll_static")

payroll_admin_bp = Blueprint(
    "payroll_admin",
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/payroll/static"
)
# ==========================
# DASHBOARD
# ==========================
@payroll_admin_bp.route('/dashboard')
@login_required
@admin_required
def payroll_dashboard():
    if current_user.role.lower() != "admin":
        return render_template("errors/403.html"), 403

    # Employee/User Stats (use HR employees for total headcount)
    total_employees = HREmployee.query.count()
    total_departments = Department.query.count()
    total_active_users = User.query.filter_by(active=True).count()
    total_inactive_users = User.query.filter_by(active=False).count()

    # Monthly Attendance Data
    today = date.today()
    first_day = today.replace(day=1)
    next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day = next_month - timedelta(days=1)

    attendance_data = (
        db.session.query(
            Attendance.date,
            func.sum(case((Attendance.status == "Present", 1), else_=0)).label("present"),
            func.sum(case((Attendance.status == "Absent", 1), else_=0)).label("absent"),
            func.sum(case((Attendance.status == "Late", 1), else_=0)).label("late")
        )
        .filter(Attendance.date >= first_day, Attendance.date <= last_day)
        .group_by(Attendance.date)
        .order_by(Attendance.date)
        .all()
    )

    monthly_dates = [a.date.strftime("%Y-%m-%d") for a in attendance_data]
    monthly_present_counts = [a.present for a in attendance_data]
    monthly_absent_counts = [a.absent for a in attendance_data]
    monthly_late_counts = [a.late for a in attendance_data]

    # Payroll Metrics
    total_disbursed = (
        db.session.query(func.sum(Payroll.net_pay))
        .filter(Payroll.status == "Paid")
        .scalar() or 0
    )

    total_deductions = (
        db.session.query(func.sum(Payroll.total_deductions))
        .filter(Payroll.status == "Paid")
        .scalar() or 0
    )

    total_gross = (
        db.session.query(func.sum(Payroll.gross_pay))
        .filter(Payroll.status == "Paid")
        .scalar() or 0
    )

    total_allowances = (
        db.session.query(func.sum(Allowance.amount)).scalar() or 0
    )

    return render_template(
        "payroll/admin/admin_dashboard.html",
        total_employees=total_employees,
        total_departments=total_departments,
        total_users=total_active_users,
        total_inactive=total_inactive_users,
        monthly_dates=monthly_dates,
        monthly_present_counts=monthly_present_counts,
        monthly_absent_counts=monthly_absent_counts,
        monthly_late_counts=monthly_late_counts,
        total_disbursed=total_disbursed,
        total_deductions=total_deductions,
        total_gross=total_gross,
        total_allowances=total_allowances
    )


# ---------------------------
# MANUAL PAYROLL
# ---------------------------
@payroll_admin_bp.route('/manual', methods=['GET', 'POST'])
@login_required
def manual_payroll():
    employees = Employee.query.all()
    payroll_periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()

    if request.method == 'POST':
        employee_id = int(request.form.get('employee_id'))
        pay_period_id = int(request.form.get('pay_period_id'))
        payroll_period = PayrollPeriod.query.get(pay_period_id)

        basic_salary = float(request.form.get('basic_salary', 0))  # hourly rate
        allowance = float(request.form.get('allowance', 0))
        sss = float(request.form.get('sss', 0))
        philhealth = float(request.form.get('philhealth', 0))
        pagibig = float(request.form.get('pagibig', 0))
        tax = float(request.form.get('tax', 0))
        other = float(request.form.get('other', 0))
        working_hours = float(request.form.get('working_hours', 0))

        # ✅ Compute net pay
        net_pay = round((basic_salary * working_hours) + allowance - (sss + philhealth + pagibig + tax + other), 2)

        payroll = Payroll(
            employee_id=employee_id,
            pay_period_id=pay_period_id,
            pay_period_start=payroll_period.start_date,
            pay_period_end=payroll_period.end_date,
            basic_salary=basic_salary,
            working_hours=working_hours,
            overtime_hours=0,
            holiday_pay=0,
            night_differential=0,
            sss_contribution=sss,
            philhealth_contribution=philhealth,
            pagibig_contribution=pagibig,
            tax_withheld=tax,
            other_deductions=other,
            net_pay=net_pay
        )

        db.session.add(payroll)
        db.session.commit()
        return jsonify({"status": "success", "net_pay": net_pay})

    # Pre-fill allowances and deductions
    employee_data = []
    for emp in employees:
        allowance_total = sum([ea.allowance.amount for ea in emp.employee_allowances])
        sss_total = sum([ed.deduction.amount for ed in emp.employee_deductions if ed.deduction.name.lower() == "sss"])
        philhealth_total = sum([ed.deduction.amount for ed in emp.employee_deductions if ed.deduction.name.lower() == "philhealth"])
        pagibig_total = sum([ed.deduction.amount for ed in emp.employee_deductions if ed.deduction.name.lower() == "pag-ibig"])

        # Fetch existing payrolls for this employee
        existing_payrolls = [p.pay_period_id for p in emp.payrolls]

        employee_data.append({
            "id": emp.id,
            "full_name": emp.get_full_name(),
            "basic_salary": emp.salary or 0,
            "allowance": allowance_total,
            "sss": sss_total,
            "philhealth": philhealth_total,
            "pagibig": pagibig_total,
            "existing_payrolls": existing_payrolls  # <-- pass this to template
        })

    return render_template(
        'payroll/admin/manual_payroll.html',
        employees=employee_data,
        payroll_periods=payroll_periods
    )

# ---------------------------
# GET WORKING HOURS
# ---------------------------
@payroll_admin_bp.route('/get_working_hours', methods=['GET'])
@login_required
def get_working_hours():
    employee_id = request.args.get('employee_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not employee_id or not start_date_str or not end_date_str:
        return jsonify({"error": "Missing parameters"}), 400

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    attendances = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    total_hours = 0
    for a in attendances:
        if a.time_in and a.time_out:
            # Start working hours at 8:00 AM if employee clocks in earlier
            work_start = max(a.time_in, time(8, 0))
            t_in = datetime.combine(a.date, work_start)
            t_out = datetime.combine(a.date, a.time_out)
            total_hours += (t_out - t_in).total_seconds() / 3600

    return jsonify({"employee_id": employee_id, "working_hours": round(total_hours, 2)})


@payroll_admin_bp.route('/employees')
@login_required
@admin_required
def view_employees():
    search = request.args.get('search', '', type=str)
    department_id = request.args.get('department_id', '', type=str)
    page = request.args.get('page', 1, type=int)

    query = HREmployee.query.options(
        joinedload(HREmployee.department),
        joinedload(HREmployee.position)
    )

   
    if search:
        query = query.filter(
            (HREmployee.first_name.ilike(f"%{search}%")) |
            (HREmployee.last_name.ilike(f"%{search}%")) |
            (HREmployee.employee_id.ilike(f"%{search}%")) |
            (HREmployee.email.ilike(f"%{search}%"))
        )

    
    if department_id:
        query = query.filter(HREmployee.department_id == department_id)

    employees = query.order_by(HREmployee.last_name).paginate(page=page, per_page=10, error_out=False)

    
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        'payroll/admin/view_employees.html',
        employees=employees,
        search=search,
        departments=departments,
        selected_department=department_id
    )


@payroll_admin_bp.route('/payrolls/edit/<int:payroll_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_payroll(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)

    if request.method == 'POST':
        payroll.basic_salary = request.form.get('basic_salary', type=float)
        payroll.gross_pay = request.form.get('gross_pay', type=float)
        payroll.total_deductions = request.form.get('total_deductions', type=float)
        payroll.net_pay = request.form.get('net_pay', type=float)
        payroll.status = request.form.get('status')
        db.session.commit()
        flash('Payroll updated successfully.', 'success')
        return redirect(url_for('payroll_admin.view_payrolls'))

    return render_template('payroll/admin/edit_payroll_details.html', payroll=payroll)

@payroll_admin_bp.route('/payrolls')
@login_required
def view_payrolls():
    search = request.args.get('search', '', type=str).strip()
    department_id = request.args.get('department_id', type=int)
    pay_period_id = request.args.get('pay_period_id', type=int)
    page = request.args.get('page', 1, type=int)

    # Base query
    query = Payroll.query.join(Employee)

    # Apply department filter
    if department_id:
        query = query.filter(Employee.department_id == department_id)

    # Apply search filter
    if search:
        query = query.filter(
            (Employee.first_name.ilike(f"%{search}%")) |
            (Employee.last_name.ilike(f"%{search}%")) |
            (Employee.employee_id.ilike(f"%{search}%"))
        )

    # Apply payroll period filter
    if pay_period_id:
        query = query.filter(Payroll.pay_period_id == pay_period_id)

    # Paginate results
    payrolls = query.order_by(Payroll.created_at.desc()).paginate(page=page, per_page=10)

    # Get department list for dropdown
    from hr_system.hr.models.hr_models import Department
    departments = Department.query.all()

    # Get payroll periods for dropdown
    from payroll_system.payroll.models.payroll_models import PayrollPeriod
    payroll_periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()

    # Get selected payroll period object
    selected_pay_period = PayrollPeriod.query.get(pay_period_id) if pay_period_id else None

    return render_template(
        'payroll/admin/view_payroll_details.html',
        payrolls=payrolls,
        search=search,
        departments=departments,
        selected_department=department_id,
        payroll_periods=payroll_periods,
        selected_pay_period=selected_pay_period
    )



@payroll_admin_bp.route('/payroll/export_excel', methods=['GET'])
@login_required
@admin_required
def export_payroll_excel():
    # Get filters from query parameters
    search = request.args.get('search', '')
    department_id = request.args.get('department_id')
    pay_period_id = request.args.get('pay_period_id')

    # Base query with eager loading for related data
    query = Payroll.query.options(
        joinedload(Payroll.employee)
            .joinedload(Employee.employee_deductions)
            .joinedload(EmployeeDeduction.deduction),
        joinedload(Payroll.employee)
            .joinedload(Employee.employee_allowances)
            .joinedload(EmployeeAllowance.allowance),
        joinedload(Payroll.employee)
            .joinedload(Employee.department)
    ).join(Payroll.employee)

    # Apply filters
    if search:
        query = query.filter(
            (Payroll.employee.first_name.ilike(f"%{search}%")) |
            (Payroll.employee.last_name.ilike(f"%{search}%"))
        )
    if department_id:
        query = query.filter(Payroll.employee.department_id == department_id)
    if pay_period_id:
        query = query.filter(Payroll.pay_period_id == pay_period_id)

    payrolls = query.all()

    # Build DataFrame
    data = []
    for p in payrolls:
        # Safely compute linked deductions and allowances
        total_linked_deductions = sum(
            (ed.deduction.amount or 0)
            for ed in getattr(p.employee, 'employee_deductions', [])
            if ed.deduction and ed.deduction.active
        )
        total_allowances = sum(
            (ea.allowance.amount or 0)
            for ea in getattr(p.employee, 'employee_allowances', [])
            if ea.allowance and ea.allowance.active
        )

        # Compute totals
        total_deductions = (p.total_deductions or 0) + total_linked_deductions
        gross_pay_with_allowances = (p.gross_pay or 0) + total_allowances

        data.append({
            "Employee ID": p.employee.employee_id,
            "Name": f"{p.employee.first_name} {p.employee.last_name}",
            "Department": p.employee.department.name if p.employee.department else "-",
            "Basic Salary": p.basic_salary or 0,
            "Overtime Hours": p.overtime_hours or 0,
            "Overtime Pay": p.overtime_pay or 0,
            "Holiday Pay": p.holiday_pay or 0,
            "Night Differential": p.night_differential or 0,
            "Allowances": total_allowances,
            "Gross Pay": gross_pay_with_allowances,
            "SSS": p.sss_contribution or 0,
            "PhilHealth": p.philhealth_contribution or 0,
            "Pag-IBIG": p.pagibig_contribution or 0,
            "Tax Withheld": p.tax_withheld or 0,
            "Other Deductions": p.other_deductions or 0,
            "Linked Deductions": total_linked_deductions,
            "Total Deductions": total_deductions,
            "Net Pay": p.net_pay or 0,
            "Status": p.status,
            "Pay Period": f"{p.pay_period_start} - {p.pay_period_end}"
        })

    df = pd.DataFrame(data)

    # Save to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Payroll')
    output.seek(0)

    # Send file to user
    filename = f"Payroll_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@payroll_admin_bp.route('/payroll-history-dashboard')
@login_required
@admin_required
def payroll_history_dashboard():
    # Fetch all employees and all payroll periods
    employees = HREmployee.query.order_by(HREmployee.last_name).all()
    periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()

    return render_template(
        "payroll/admin/admin_history_dashboard.html",
        employees=employees,
        periods=periods
    )


# Employee Payroll History
@payroll_admin_bp.route('/employees/<int:employee_id>/payroll-history')
@login_required
@admin_required
def view_employee_payroll_history(employee_id):
    # Get employee or return 404
    employee = HREmployee.query.get_or_404(employee_id)

    # Fetch payroll records for this employee
    payroll_records = (
        Payroll.query.join(Employee, Payroll.employee_id == Employee.id)
        .filter(Employee.id == employee.id)
        .order_by(Payroll.created_at.desc())
        .all()
    )

    return render_template(
        "payroll/admin/payroll_employee_history.html",
        employee=employee,
        payroll_records=payroll_records
    )

@payroll_admin_bp.route('/payroll-periods/<int:period_id>/history')
@login_required
@admin_required
def payroll_period_history(period_id):
    # Get payroll period or 404
    period = PayrollPeriod.query.get_or_404(period_id)

    # Fetch all payrolls for this period using the correct column
    payroll_records = (
        Payroll.query.join(Employee)
        .filter(Payroll.pay_period_id == period.id)  # <-- corrected
        .order_by(Employee.last_name)
        .all()
    )

    return render_template(
        "payroll/admin/payroll_periods_history.html",
        period=period,
        payroll_records=payroll_records
    )




# ==========================
# SYNC EMPLOYEES
# ==========================
@payroll_admin_bp.route('/employees/sync', methods=['POST'])
@login_required
@admin_required
def sync_employees():
    try:
        hr_employees = sync_all_employees_from_hr()
        if not hr_employees:
            flash('No employees found in HR system or sync failed.', 'error')
            return redirect(url_for('payroll_admin.employees'))

        synced_count = 0
        for emp_data in hr_employees:
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
                    date_hired=datetime.strptime(emp_data['date_hired'], '%Y-%m-%d').date()
                    if emp_data.get('date_hired') else date.today(),
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

    except Exception:
        db.session.rollback()
        flash('Error syncing employees. Please try again.', 'error')

    return redirect(url_for('payroll_admin.employees'))


# ==========================
# PAYROLL PERIODS
# ==========================

from flask import request

@payroll_admin_bp.route('/payroll-periods')
@login_required
@admin_required
def view_payroll_periods():
    # Get filters from query parameters
    status_filter = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Base query
    query = PayrollPeriod.query

    # Apply filters
    if status_filter:
        query = query.filter_by(status=status_filter)
    if start_date:
        query = query.filter(PayrollPeriod.start_date >= start_date)
    if end_date:
        query = query.filter(PayrollPeriod.end_date <= end_date)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Change as needed
    periods_paginated = query.order_by(PayrollPeriod.id.desc()).paginate(page=page, per_page=per_page)

    return render_template(
        'payroll/admin/view_periods.html',
        periods=periods_paginated.items,
        pagination=periods_paginated
    )



@payroll_admin_bp.route('/payroll-periods/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_payroll_period():

    if request.method == 'POST':
        try:
            period_name = request.form.get('period_name').strip()

            # Convert string to Python date objects
            start_date = datetime.strptime(request.form.get('start_date'), "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form.get('end_date'), "%Y-%m-%d").date()
            pay_date = datetime.strptime(request.form.get('pay_date'), "%Y-%m-%d").date()

            new_period = PayrollPeriod(
                period_name=period_name,
                start_date=start_date,
                end_date=end_date,
                pay_date=pay_date,
                status="Open"
            )

            db.session.add(new_period)
            db.session.commit()

            flash(f'Payroll period "{period_name}" created successfully!', 'success')
            return redirect(url_for('payroll_admin.view_payroll_periods'))

        except Exception as e:
            db.session.rollback()
            print(f"Error creating payroll period: {e}")
            flash('An error occurred while creating the payroll period. Please try again.', 'danger')

    return render_template('payroll/admin/add_payroll_period.html')



@payroll_admin_bp.route('/payroll-periods/edit/<int:period_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_payroll_period(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)

    if request.method == 'POST':
        period.period_name = request.form.get('period_name')
        # Convert string to date objects
        period.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        period.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        period.pay_date = datetime.strptime(request.form.get('pay_date'), '%Y-%m-%d').date()
        period.status = request.form.get('status')
        
        db.session.commit()
        flash('Payroll period updated successfully.', 'success')
        return redirect(url_for('payroll_admin.view_payroll_periods'))

    return render_template('payroll/admin/edit_payroll_period.html', payroll_period=period)



@payroll_admin_bp.route('/payroll-periods/delete/<int:period_id>', methods=['POST'])
@login_required
@admin_required
def delete_payroll_period(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    db.session.delete(period)
    db.session.commit()
    flash('Payroll period deleted successfully.', 'success')
    return redirect(url_for('payroll_admin.view_payroll_periods'))


# ==========================
# PAYROLL
# ==========================

@payroll_admin_bp.route('/payroll/details/<int:period_id>')
@login_required
@admin_required
def payroll_details(period_id):
    period = PayrollPeriod.query.get_or_404(period_id)
    
    payrolls = (
        Payroll.query
        .join(Employee)
        .filter(Payroll.pay_period_id == period_id)
        .order_by(Employee.last_name.asc())
        .all()
    )

    # Ensure calculations are correct
    for p in payrolls:
        p.calculate_earnings()  # updates gross_pay, total_deductions, net_pay

    total_gross = sum(p.gross_pay for p in payrolls)
    total_deductions = sum(p.total_deductions for p in payrolls)
    total_net = sum(p.net_pay for p in payrolls)

    return render_template(
        'payroll/admin/payroll_details.html',
        period=period,
        payrolls=payrolls,
        total_gross=total_gross,
        total_deductions=total_deductions,
        total_net=total_net
    )


# -----------------------------
# Helper: Apply allowances/deductions
# -----------------------------
def apply_allowances_and_deductions(employee, gross_pay):
    total_allowances = 0
    total_deductions = 0

    for ea in getattr(employee, 'employee_allowances', []):
        allowance = ea.allowance
        if not allowance.active:
            continue
        if allowance.type.lower() == 'fixed':
            total_allowances += allowance.amount
        else:
            total_allowances += gross_pay * allowance.percentage / 100

    for ed in getattr(employee, 'employee_deductions', []):
        deduction = ed.deduction
        if not deduction.active:
            continue
        if deduction.type.lower() == 'fixed':
            total_deductions += deduction.amount
        else:
            total_deductions += gross_pay * deduction.percentage / 100

    return total_allowances, total_deductions


# -----------------------------
# Payroll page
# -----------------------------
@payroll_admin_bp.route('/payroll')
@login_required
@admin_required
def payroll():
    periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()
    employees = Employee.query.filter_by(active=True).all()
    return render_template(
        'payroll/admin/process_payroll.html',
        periods=periods,
        employees=employees
    )



# Helper functions
# -----------------------------
def get_working_hours(attendance):
    """Return working hours as float from time_in and time_out."""
    total_hours = 0
    for a in attendance:
        if a.time_in and a.time_out and a.status == "Present":
            delta = datetime.combine(datetime.min, a.time_out) - datetime.combine(datetime.min, a.time_in)
            hours = delta.total_seconds() / 3600
            total_hours += hours
    return total_hours

def get_employee_allowances(employee):
    """Sum of all employee allowances (amount or % of salary)."""
    total = 0
    for ea in employee.employee_allowances:
        allowance = ea.allowance
        if allowance.amount:
            total += allowance.amount
        elif allowance.percentage:
            total += (allowance.percentage / 100) * (employee.salary or 0)
    return total

def get_employee_deductions(employee):
    """Sum of all employee deductions (amount or % of salary)."""
    total = 0
    for ed in employee.employee_deductions:
        deduction = ed.deduction
        if deduction.amount:
            total += deduction.amount
        elif deduction.percentage:
            total += (deduction.percentage / 100) * (employee.salary or 0)
    return total



# -----------------------------
# Process Payroll Preview
# -----------------------------
@payroll_admin_bp.route('/payroll/process', methods=['POST', 'GET'])
@login_required
@admin_required
def process_payroll():
    period_id = request.form.get('payroll_period_id', type=int)
    periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()
    employees = Employee.query.filter_by(active=True).all()

    if not period_id:
        flash('Please select a payroll period.', 'form_error')
        return render_template('payroll/admin/process_payroll.html', periods=periods, employees=employees)

    period = PayrollPeriod.query.get_or_404(period_id)

    if period.status.lower() != 'open':
        flash('This payroll period is not open for processing.', 'error')
        return render_template('payroll/admin/process_payroll.html', periods=periods, employees=employees)

    preview_payrolls = []

    for emp in employees:
        existing = Payroll.query.filter_by(employee_id=emp.id, pay_period_id=period.id).first()
        if existing:
            continue

        attendance_records = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= period.start_date,
            Attendance.date <= period.end_date
        ).all()

        # Compute total working hours
        total_hours = sum(
            (datetime.combine(date.min, a.time_out) - datetime.combine(date.min, a.time_in)).total_seconds() / 3600
            for a in attendance_records if a.time_in and a.time_out
        )

        hourly_rate = emp.salary or 0  # Assuming you have hourly_rate field

        # Basic salary based on worked hours
        basic_salary = round(total_hours * hourly_rate, 2)

        # Compute additional pay
        overtime_hours = sum(getattr(a, 'overtime_hours', 0) for a in attendance_records)
        holiday_hours = sum(getattr(a, 'holiday_hours', 0) for a in attendance_records)
        night_hours = sum(getattr(a, 'night_hours', 0) for a in attendance_records)

        overtime_pay = round(hourly_rate * 1.25 * overtime_hours, 2)
        holiday_pay = round(hourly_rate * 2.0 * holiday_hours, 2)
        night_diff = round(hourly_rate * 1.10 * night_hours, 2)

        # Allowances
        allowances_total = sum(link.allowance.amount for link in emp.employee_allowances if link.allowance.active)

        gross = basic_salary + overtime_pay + holiday_pay + night_diff + allowances_total

        # Deductions
        deductions_total = sum(link.deduction.amount for link in emp.employee_deductions if link.deduction.active)
        sss = round(0.045 * basic_salary, 2)
        philhealth = round(0.0275 * basic_salary, 2)
        pagibig = 100
        taxable_income = gross - (sss + philhealth + pagibig + deductions_total)
        tax = round(taxable_income * 0.10, 2)

        total_deductions = sss + philhealth + pagibig + tax + deductions_total
        net_pay = gross - total_deductions

        preview_payrolls.append({
            "employee": emp,
            "basic_salary": basic_salary,
            "working_hours": total_hours,
            "overtime_pay": overtime_pay,
            "holiday_pay": holiday_pay,
            "night_diff": night_diff,
            "gross": gross,
            "allowances": allowances_total,
            "total_deductions": total_deductions,
            "net_pay": net_pay,
            "status": "Processed" if total_hours > 0 else "Absent"
        })

    return render_template(
        'payroll/admin/process_payroll.html',
        periods=periods,
        employees=employees,
        preview_payrolls=preview_payrolls,
        preview_period=period
    )


# -----------------------------
# Confirm Payroll
# -----------------------------
@payroll_admin_bp.route('/payroll/confirm', methods=['POST'])
@login_required
@admin_required
def confirm_payroll():
    period_id = request.form.get('period_id', type=int)
    if not period_id:
        flash("No payroll period selected.", "error")
        return redirect(url_for("payroll_admin.payroll"))

    period = PayrollPeriod.query.get_or_404(period_id)
    if period.status.lower() != "open":
        flash("Payroll period is not open for processing.", "error")
        return redirect(url_for("payroll_admin.payroll"))

    employees = Employee.query.filter_by(active=True).all()
    saved_count = 0

    for emp in employees:
        existing = Payroll.query.filter_by(employee_id=emp.id, pay_period_id=period.id).first()
        if existing:
            continue

        attendance_records = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= period.start_date,
            Attendance.date <= period.end_date
        ).all()

        total_hours = sum(
            (datetime.combine(date.min, a.time_out) - datetime.combine(date.min, a.time_in)).total_seconds() / 3600
            for a in attendance_records if a.time_in and a.time_out
        )

        hourly_rate = emp.salary or 0
        basic_salary = round(total_hours * hourly_rate, 2)

        overtime_hours = sum(getattr(a, 'overtime_hours', 0) for a in attendance_records)
        holiday_hours = sum(getattr(a, 'holiday_hours', 0) for a in attendance_records)
        night_hours = sum(getattr(a, 'night_hours', 0) for a in attendance_records)

        overtime_pay = round(hourly_rate * 1.25 * overtime_hours, 2)
        holiday_pay = round(hourly_rate * 2.0 * holiday_hours, 2)
        night_diff = round(hourly_rate * 1.10 * night_hours, 2)

        allowances_total = sum(link.allowance.amount for link in emp.employee_allowances if link.allowance.active)
        gross = basic_salary + overtime_pay + holiday_pay + night_diff + allowances_total

        deductions_total = sum(link.deduction.amount for link in emp.employee_deductions if link.deduction.active)
        sss = round(0.045 * basic_salary, 2)
        philhealth = round(0.0275 * basic_salary, 2)
        pagibig = 100
        taxable_income = gross - (sss + philhealth + pagibig + deductions_total)
        tax = round(taxable_income * 0.10, 2)
        total_deductions = sss + philhealth + pagibig + tax + deductions_total
        net_pay = gross - total_deductions

        payroll_record = Payroll(
            employee_id=emp.id,
            pay_period_id=period.id,
            pay_period_start=period.start_date,
            pay_period_end=period.end_date,
            basic_salary=basic_salary,
            working_hours=total_hours,
            overtime_hours=overtime_hours,
            overtime_pay=overtime_pay,
            holiday_pay=holiday_pay,
            night_differential=night_diff,
            gross_pay=gross,
            other_deductions=deductions_total,
            total_deductions=total_deductions,
            net_pay=net_pay,
            status="Processed" if total_hours > 0 else "Absent"
        )
        db.session.add(payroll_record)
        saved_count += 1

    db.session.commit()
    flash(f"Payroll saved for employee(s).", "success")
    return redirect(url_for("payroll_admin.payroll"))



@payroll_admin_bp.route('/payslips')
@login_required
@admin_required
def view_payslips():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    department_id = request.args.get('department_id', '', type=str)
    status = request.args.get('status', '', type=str)
    period_id = request.args.get('period_id', '', type=str)

    # Base query with joins
    query = Payslip.query.join(Employee).join(Department, isouter=True)

    # 🔍 Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Payslip.payslip_number.ilike(search_pattern),
                Employee.first_name.ilike(search_pattern),
                Employee.last_name.ilike(search_pattern)
            )
        )

    # 🏢 Department filter
    if department_id:
        query = query.filter(Employee.department_id == department_id)

    # 🧾 Status filter (map UI → DB)
    if status:
        if status == "Not Claimed":
            query = query.filter(Payslip.status == "Generated")
        elif status == "Claimed":
            query = query.filter(Payslip.status == "Distributed")
        # else: if empty, show all

    # 📅 Payroll Period filter
    if period_id:
        query = query.filter(Payslip.payroll_id == period_id)

    # Sort newest first
    payslips = query.order_by(Payslip.generated_at.desc()).paginate(page=page, per_page=20, error_out=False)

    # Dropdown data
    departments = Department.query.order_by(Department.name.asc()).all()
    payroll_periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()

    return render_template(
        'payroll/admin/payslips.html',
        payslips=payslips,
        search=search,
        departments=departments,
        selected_department=department_id,
        selected_status=status,
        payroll_periods=payroll_periods,
        selected_period=period_id
    )




# =========================================================
# MARK AS DISTRIBUTED / CLAIMED
# =========================================================
@payroll_admin_bp.route('/payslips/distribute/<int:payslip_id>', methods=['POST'])
@login_required
@admin_required
def distribute_payslip(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)

    if payslip.status == "Distributed":
        flash("Payslip already marked as distributed (claimed).", "info")
        return redirect(url_for('payroll_admin.view_payslips'))

    payslip.status = "Distributed"
    payslip.claimed = True  # ✅ Mark as claimed when distributed
    payslip.distributed_at = datetime.utcnow()
    db.session.commit()

    flash(f"Payslip {payslip.payslip_number} marked as distributed and claimed.", "success")
    return redirect(url_for('payroll_admin.view_payslips'))

# =========================================================
# GENERATE PAYSLIPS BY PAYROLL PERIOD (SELECT PERIOD)
# =========================================================
@payroll_admin_bp.route('/payslips/generate', methods=['GET', 'POST'])
@login_required
@admin_required
def generate_payslips_by_period():
    # Get all payroll periods
    payroll_periods = PayrollPeriod.query.order_by(PayrollPeriod.start_date.desc()).all()

    if request.method == 'POST':
        pay_period_id = request.form.get('pay_period_id')
        if not pay_period_id:
            flash("Please select a payroll period.", "warning")
            return redirect(url_for('payroll_admin.generate_payslips_by_period'))

        # Fetch payrolls for selected period
        payrolls = Payroll.query.filter_by(pay_period_id=pay_period_id).all()
        if not payrolls:
            flash("No payrolls found for this pay period.", "warning")
            return redirect(url_for('payroll_admin.generate_payslips_by_period'))

        generated_by_id = current_user.id
        generated_count = 0

        for payroll in payrolls:
            existing = Payslip.query.filter_by(payroll_id=payroll.id).first()
            if existing:
                continue  # Skip if payslip already exists
            payslip = generate_payslip(payroll, generated_by_id)
            db.session.add(payslip)
            generated_count += 1

        db.session.commit()
        flash(f"{generated_count} payslips successfully generated for the selected period.", "success")
        return redirect(url_for('payroll_admin.view_payslips'))

    # GET: Render selection form
    return render_template('payroll/admin/generate_payslips.html', payroll_periods=payroll_periods)



# =========================================================
# GENERATE SINGLE PAYSLIP
# =========================================================
@payroll_admin_bp.route('/payslips/generate/<int:payroll_id>', methods=['POST'])
@login_required
@admin_required
def generate_single_payslip(payroll_id):
    payroll = Payroll.query.get_or_404(payroll_id)

    existing = Payslip.query.filter_by(payroll_id=payroll.id).first()
    if existing:
        flash("Payslip already exists for this employee.", "info")
        return redirect(url_for('payroll_admin.view_payslips'))

    payslip = generate_payslip(payroll, current_user.id)
    db.session.add(payslip)
    db.session.commit()

    flash(f"Payslip generated for employee ID {payroll.employee_id}.", "success")
    return redirect(url_for('payroll_admin.view_payslips'))


# =========================================================
# HELPER FUNCTION
# =========================================================
def generate_payslip(payroll, generated_by_id=None):
    payslip = Payslip(
        employee_id=payroll.employee_id,
        payroll_id=payroll.id,
        payslip_number=f"PS-{payroll.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        pay_period_start=payroll.pay_period_start,
        pay_period_end=payroll.pay_period_end,
        basic_salary=payroll.basic_salary,
        overtime_pay=payroll.overtime_pay,
        holiday_pay=payroll.holiday_pay,
        night_differential=payroll.night_differential,
        gross_pay=payroll.gross_pay,
        sss_contribution=payroll.sss_contribution,
        philhealth_contribution=payroll.philhealth_contribution,
        pagibig_contribution=payroll.pagibig_contribution,
        tax_withheld=payroll.tax_withheld,
        total_deductions=payroll.total_deductions,
        net_pay=payroll.net_pay,
        generated_by=generated_by_id
    )
    db.session.add(payslip)
    return payslip

# =========================================================
# REVIEW & APPROVE PAYSLIPS (TABLE VIEW)
# =========================================================
@payroll_admin_bp.route('/payslips/review', methods=['GET', 'POST'])
@login_required
@admin_required
def review_payslips():
    if request.method == 'POST':
        action = request.form.get('action')

        # Bulk approve all
        if action == 'approve_all':
            payslips = Payslip.query.filter(Payslip.status == "Generated").all()
            for p in payslips:
                p.status = "Approved"
                p.approved_by = current_user.id
                p.approved_at = datetime.utcnow()
            db.session.commit()
            flash(f"All generated payslips approved successfully.", "success")
            return redirect(url_for('payroll_admin.review_payslips'))

        # Individual approve/reject
        payslip_id = request.form.get('payslip_id')
        decision = request.form.get('decision')
        reason = request.form.get('reason', '').strip()
        payslip = Payslip.query.get_or_404(payslip_id)

        if payslip.status in ["Approved", "Rejected", "Distributed"]:
            flash(f"Payslip {payslip.payslip_number} already {payslip.status.lower()}.", "info")
            return redirect(url_for('payroll_admin.review_payslips'))

        if decision == 'approve':
            payslip.status = "Approved"
            payslip.approved_by = current_user.id
            payslip.approved_at = datetime.utcnow()
            payslip.rejection_reason = None
            flash(f"Payslip {payslip.payslip_number} approved.", "success")
        elif decision == 'reject':
            payslip.status = "Rejected"
            payslip.approved_by = current_user.id
            payslip.approved_at = datetime.utcnow()
            payslip.rejection_reason = reason or "No reason provided."
            flash(f"Payslip {payslip.payslip_number} rejected.", "danger")

        db.session.commit()
        return redirect(url_for('payroll_admin.review_payslips'))

    # GET: Load table
    payslips = Payslip.query.order_by(Payslip.generated_at.desc()).all()
    return render_template('payroll/admin/review_payslips.html', payslips=payslips)

# =========================================================
# APPROVE PAYSLIP
# =========================================================
@payroll_admin_bp.route('/payslips/approve/<int:payslip_id>', methods=['POST'])
@login_required
@admin_required
def approve_payslip(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)

    if payslip.status in ["Approved", "Rejected", "Distributed"]:
        flash(f"Payslip {payslip.payslip_number} has already been {payslip.status.lower()}.", "info")
        return redirect(url_for('payroll_admin.view_payslips'))

    payslip.status = "Approved"
    payslip.approved_by = current_user.id
    payslip.approved_at = datetime.utcnow()
    db.session.commit()

    flash(f"Payslip {payslip.payslip_number} approved successfully.", "success")
    return redirect(url_for('payroll_admin.view_payslips'))


# =========================================================
# REJECT PAYSLIP
# =========================================================
@payroll_admin_bp.route('/payslips/reject/<int:payslip_id>', methods=['POST'])
@login_required
@admin_required
def reject_payslip(payslip_id):
    payslip = Payslip.query.get_or_404(payslip_id)
    reason = request.form.get('reason', '').strip()

    if payslip.status in ["Approved", "Rejected", "Distributed"]:
        flash(f"Payslip {payslip.payslip_number} has already been {payslip.status.lower()}.", "info")
        return redirect(url_for('payroll_admin.view_payslips'))

    payslip.status = "Rejected"
    payslip.rejection_reason = reason or "No reason provided"
    db.session.commit()

    flash(f"Payslip {payslip.payslip_number} rejected. Reason: {payslip.rejection_reason}", "warning")
    return redirect(url_for('payroll_admin.view_payslips'))




# ==========================
# DEDUCTIONS
# ==========================
@payroll_admin_bp.route('/deductions')
@login_required
@admin_required
def deductions():
    search = request.args.get('search', '', type=str).strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # You can adjust how many per page

    # Base query
    query = Deduction.query

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            Deduction.name.ilike(search_pattern) |
            Deduction.description.ilike(search_pattern) |
            Deduction.type.ilike(search_pattern)
        )

    # Paginate
    deductions_paginated = query.order_by(Deduction.id.desc()).paginate(page=page, per_page=per_page)

    return render_template(
        'payroll/admin/deductions.html',
        deductions=deductions_paginated.items,
        pagination=deductions_paginated,
        search=search
    )


@payroll_admin_bp.route('/deductions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_deduction():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        type_ = request.form.get('type')
        amount = request.form.get('amount') or 0
        percentage = request.form.get('percentage') or 0
        is_mandatory = bool(int(request.form.get('is_mandatory', 0)))
        active = bool(int(request.form.get('active', 1)))

        deduction = Deduction(
            name=name,
            description=description,
            type=type_,
            amount=float(amount),
            percentage=float(percentage),
            is_mandatory=is_mandatory,
            active=active
        )

        try:
            db.session.add(deduction)
            db.session.commit()
            flash('Deduction added successfully!', 'success')


            return redirect(url_for('payroll_admin.deductions'))

        except Exception as e:
            db.session.rollback()
            print("Error adding deduction:", e)
            flash('Error adding deduction. Please try again.', 'error')

    return render_template('payroll/admin/deduction_add.html')




@payroll_admin_bp.route('/deductions/<int:deduction_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_deduction(deduction_id):
    deduction = Deduction.query.get_or_404(deduction_id)

    # If AJAX request, return only the modal form HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('payroll/admin/deduction_edit.html', deduction=deduction)

    # Normal POST submission (redirect back)
    if request.method == 'POST':
        try:
            deduction.name = request.form.get('name')
            deduction.description = request.form.get('description')
            deduction.type = request.form.get('type')
            deduction.amount = float(request.form.get('amount') or 0)
            deduction.percentage = float(request.form.get('percentage') or 0)
            deduction.is_mandatory = request.form.get('is_mandatory') == '1'
            deduction.active = request.form.get('active') == '1'
            db.session.commit()
            flash('Deduction updated successfully!', 'success')
            return redirect(url_for('payroll_admin.deductions'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating deduction: ' + str(e), 'error')
            return redirect(url_for('payroll_admin.deductions'))

    return render_template('payroll/admin/deduction_edit.html', deduction=deduction)





# ==========================
# ALLOWANCES
# ==========================
@payroll_admin_bp.route('/allowances')
@login_required
@admin_required
def allowances():
    search = request.args.get('search', '', type=str).strip()
    page = request.args.get('page', 1, type=int)

    query = Allowance.query

    if search:
        query = query.filter(Allowance.name.ilike(f"%{search}%"))

    pagination = query.paginate(page=page, per_page=10)
    allowances = pagination.items

    return render_template(
        'payroll/admin/allowances.html',
        allowances=allowances,
        pagination=pagination,
        search=search,
    )



@payroll_admin_bp.route('/allowances/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_allowance():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        type_ = request.form.get('type')
        amount = request.form.get('amount') or 0
        percentage = request.form.get('percentage') or 0
        active = True if request.form.get('active') == '1' else False

        new_allowance = Allowance(
            name=name,
            description=description,
            type=type_,
            amount=float(amount),
            percentage=float(percentage),
            active=active
        )

        try:
            db.session.add(new_allowance)
            db.session.commit()
            return jsonify({
                'success': True,
                'redirect': url_for('payroll_admin.allowance')  # <-- redirect URL
            })
        except Exception:
            db.session.rollback()
            return jsonify({'success': False})


    return render_template('payroll/admin/allowance_add.html')

# ==========================
# TAX BRACKETS
# ==========================
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
        except Exception:
            db.session.rollback()
            flash('Error adding tax bracket. Please try again.', 'error')

    return render_template('payroll/add_tax_bracket.html', form=form)


# ==========================
# REPORTS
# ==========================
@payroll_admin_bp.route('/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def reports():
    form = PayrollSummaryForm()
    form.period_id.choices = [(p.id, f"{p.period_name} ({p.start_date} to {p.end_date})") for p in PayrollPeriod.query.all()]

    summary = None
    if form.validate_on_submit():
        summary = calculate_payroll_summary(form.period_id.data, form.department.data)

    return render_template('payroll/reports.html', form=form, summary=summary)


@payroll_admin_bp.route('/payroll/admin/summary', methods=['GET'])
@login_required
@admin_required
def payroll_summary():
    department_id = request.args.get('department_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # adjust as you prefer

    query = db.session.query(
        Department.name.label('department_name'),
        func.sum(Payroll.gross_pay).label('total_gross'),
        func.sum(Payroll.total_deductions).label('total_deductions'),
        func.sum(Payroll.net_pay).label('total_net')
    ).join(Employee, Payroll.employee_id == Employee.id
    ).join(Department, Employee.department_id == Department.id
    ).group_by(Department.name)

    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if start_date and end_date:
        query = query.filter(Payroll.pay_period_start >= start_date,
                             Payroll.pay_period_end <= end_date)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    departments = Department.query.all()

    return render_template(
        'payroll/admin/summary_reports.html',
        results=pagination.items,
        departments=departments,
        pagination=pagination,
        selected_department=department_id,
        start_date=start_date,
        end_date=end_date
    )



@payroll_admin_bp.route('/payroll/admin/export_excel')
@admin_required
@login_required
def export_excel():
    department_id = request.args.get('department_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = db.session.query(
        Department.name.label('Department'),
        func.sum(Payroll.gross_pay).label('Total Gross'),
        func.sum(Payroll.total_deductions).label('Total Deductions'),
        func.sum(Payroll.net_pay).label('Total Net')
    ).join(Employee, Payroll.employee_id == Employee.id
    ).join(Department, Employee.department_id == Department.id
    ).group_by(Department.name)

    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if start_date and end_date:
        query = query.filter(
            Payroll.pay_period_start >= start_date,
            Payroll.pay_period_end <= end_date
        )

    # ✅ FIX HERE — use db.engine.connect()
    with db.engine.connect() as connection:
        df = pd.read_sql(query.statement, connection)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        download_name="payroll_summary.xlsx",
        as_attachment=True
    )

@payroll_admin_bp.route('/payroll/admin/export_pdf')
@admin_required
@login_required
def export_pdf():
    department_id = request.args.get('department_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # 🧮 Query payroll summary
    query = db.session.query(
        Department.name.label('department_name'),
        func.sum(Payroll.gross_pay).label('total_gross'),
        func.sum(Payroll.total_deductions).label('total_deductions'),
        func.sum(Payroll.net_pay).label('total_net')
    ).join(Employee, Payroll.employee_id == Employee.id
    ).join(Department, Employee.department_id == Department.id
    ).group_by(Department.name)

    # 🔍 Apply filters if provided
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if start_date and end_date:
        query = query.filter(
            Payroll.pay_period_start >= start_date,
            Payroll.pay_period_end <= end_date
        )

    results = query.all()

    # 🧾 Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # 🏷️ Title
    title_text = "Payroll Summary Report"
    elements.append(Paragraph(title_text, styles['Title']))
    elements.append(Spacer(1, 12))

    # 📅 Filters Info (Optional)
    filter_info = []
    if department_id:
        dept = Department.query.get(department_id)
        if dept:
            filter_info.append(f"Department: {dept.name}")
    if start_date and end_date:
        filter_info.append(f"Period: {start_date} to {end_date}")

    if filter_info:
        elements.append(Paragraph(", ".join(filter_info), styles['Normal']))
        elements.append(Spacer(1, 12))

    # 🧮 Table Data
    data = [["Department", "Total Gross", "Total Deductions", "Total Net"]]

    if results:
        for r in results:
            total_gross = r.total_gross or 0.00
            total_deductions = r.total_deductions or 0.00
            total_net = r.total_net or 0.00

            data.append([
                r.department_name,
                f"₱ {total_gross:,.2f}",
                f"₱ {total_deductions:,.2f}",
                f"₱ {total_net:,.2f}"
            ])
    else:
        data.append(["No records found", "", "", ""])

    # 🎨 Table Styling
    table = Table(data, hAlign='CENTER')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))

    elements.append(table)

    # 📄 Build and return PDF
    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, download_name="payroll_summary.pdf", as_attachment=True)

@payroll_admin_bp.route('/payroll/admin/generate_payroll', methods=['POST'])
@admin_required
@login_required
def generate_payrolls():
    from datetime import date, datetime, timedelta

    year = int(request.form.get('year'))
    month = int(request.form.get('month'))

    # ✅ Step 1: Get start and end date for the selected month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    # ✅ Step 2: Automatically get or create PayrollPeriod
    payroll_period = PayrollPeriod.query.filter_by(
        start_date=start_date,
        end_date=end_date
    ).first()

    if not payroll_period:
        payroll_period = PayrollPeriod(
            start_date=start_date,
            end_date=end_date,
            description=f"{start_date.strftime('%B %Y')} Payroll"
        )
        db.session.add(payroll_period)
        db.session.commit()

    # ✅ Step 3: Generate payrolls for each employee
    employees = Employee.query.all()
    generated_count = 0

    for emp in employees:
        logs = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()

        total_hours = 0
        for log in logs:
            if log.time_in and log.time_out:
                delta = log.time_out - log.time_in
                total_hours += delta.total_seconds() / 3600

        if total_hours <= 0:
            continue

        existing_payroll = Payroll.query.filter_by(
            employee_id=emp.id,
            pay_period_id=payroll_period.id
        ).first()

        if existing_payroll:
            continue  # skip if already generated

        payroll = Payroll(
            employee_id=emp.id,
            pay_period_id=payroll_period.id,
            pay_period_start=start_date,
            pay_period_end=end_date,
            basic_salary=emp.basic_salary or 0,
            working_hours=total_hours
        )
        payroll.calculate_earnings()
        db.session.add(payroll)
        generated_count += 1

    db.session.commit()
    flash(f"Payroll generated for {generated_count} employees for {start_date.strftime('%B %Y')}.", "success")
    return redirect(url_for('payroll_admin.earnings_report'))


@payroll_admin_bp.route('/payroll/admin/earnings_report')
@login_required
def earnings_report():
    report_type = request.args.get('type', 'monthly')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    # 🧮 Compute total hours worked per employee (SQLite-compatible)
    subquery = db.session.query(
        Attendance.employee_id,
        func.sum(
            (
                func.strftime('%s', func.concat(Attendance.date, ' ', Attendance.time_out)) -
                func.strftime('%s', func.concat(Attendance.date, ' ', Attendance.time_in))
            ) / 3600.0  # convert seconds to hours
        ).label('total_hours')
    )

    if report_type == 'monthly':
        subquery = subquery.filter(
            extract('year', Attendance.date) == year,
            extract('month', Attendance.date) == month
        )
    elif report_type == 'annual':
        subquery = subquery.filter(extract('year', Attendance.date) == year)

    subquery = subquery.group_by(Attendance.employee_id).subquery()

    # 🧾 Join employee + computed total hours
    query = db.session.query(
        Employee.id,
        Employee.first_name,
        Employee.last_name,
        Employee.salary,
        func.coalesce(subquery.c.total_hours, 0).label('total_hours'),
        (func.coalesce(subquery.c.total_hours, 0) * (Employee.salary / 160)).label('total_earnings')
    ).outerjoin(subquery, Employee.id == subquery.c.employee_id)

    reports = query.all()

    return render_template(
        'payroll/admin/earnings_report.html',
        reports=reports,
        report_type=report_type,
        year=year,
        month=month
    )


# =========================================================
# 🧾 EXPORT EARNINGS REPORT AS PDF
# =========================================================
@payroll_admin_bp.route('/export_earnings_pdf')
@login_required
def export_earnings_pdf():
    """Export the employee earnings report to a PDF file."""
    report_type = request.args.get('type', 'monthly')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    query = db.session.query(
        Employee.first_name,
        Employee.last_name,
        func.sum(Payroll.working_hours).label('total_hours'),
        func.sum(Payroll.gross_pay).label('total_gross'),
        func.sum(Payroll.total_deductions).label('total_deductions'),
        func.sum(Payroll.net_pay).label('total_net')
    ).join(Payroll, Payroll.employee_id == Employee.id)

    if report_type == 'monthly':
        query = query.filter(
            extract('year', Payroll.pay_period_start) == year,
            extract('month', Payroll.pay_period_start) == month
        )
    else:
        query = query.filter(extract('year', Payroll.pay_period_start) == year)

    results = query.group_by(Employee.id).all()

    # --- Generate PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 80

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Employee Earnings Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y - 20, f"Report Type: {report_type.capitalize()} | Year: {year}")
    if report_type == 'monthly':
        pdf.drawString(400, y - 20, f"Month: {month}")

    # Header
    y -= 50
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Employee")
    pdf.drawString(220, y, "Hours")
    pdf.drawString(300, y, "Gross Pay")
    pdf.drawString(400, y, "Deductions")
    pdf.drawString(500, y, "Net Pay")
    pdf.line(50, y - 2, 550, y - 2)
    y -= 20

    pdf.setFont("Helvetica", 10)
    for emp in results:
        if y < 100:
            pdf.showPage()
            y = height - 100
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(50, y, "Employee")
            pdf.drawString(220, y, "Hours")
            pdf.drawString(300, y, "Gross Pay")
            pdf.drawString(400, y, "Deductions")
            pdf.drawString(500, y, "Net Pay")
            pdf.line(50, y - 2, 550, y - 2)
            pdf.setFont("Helvetica", 10)
            y -= 20

        hours = emp.total_hours or 0
        gross = emp.total_gross or 0
        deductions = emp.total_deductions or 0
        net = emp.total_net or 0

        pdf.drawString(50, y, f"{emp.first_name} {emp.last_name}")
        pdf.drawRightString(270, y, f"{hours:.2f}")
        pdf.drawRightString(370, y, f"₱{gross:,.2f}")
        pdf.drawRightString(470, y, f"₱{deductions:,.2f}")
        pdf.drawRightString(560, y, f"₱{net:,.2f}")
        y -= 18

    pdf.save()
    buffer.seek(0)

    filename = f"earnings_report_{report_type}_{year}"
    if report_type == 'monthly':
        filename += f"_{month:02d}"
    filename += ".pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


@payroll_admin_bp.route('/employees/benefits')
@login_required
@admin_required
def list_employee_benefits():
    employees = Employee.query.all()
    return render_template('payroll/admin/manage_benefits_list.html', employees=employees)

    
@payroll_admin_bp.route('/employee/<int:employee_id>/benefits/<string:benefit_type>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_employee_benefits(employee_id, benefit_type):
    employee = Employee.query.get_or_404(employee_id)

    if benefit_type == "deductions":
        all_items = Deduction.query.all()
        selected_items = [link.deduction_id for link in employee.employee_deductions]
    elif benefit_type == "allowances":
        all_items = Allowance.query.all()
        selected_items = [link.allowance_id for link in employee.employee_allowances]
    else:
        flash("Invalid benefit type.", "danger")
        return redirect(url_for('payroll_admin.list_employee_benefits'))

    success_message = None

    if request.method == "POST":
        selected_ids = [int(i) for i in request.form.getlist('selected_items')]

        try:
            if benefit_type == "deductions":
                # remove existing links
                EmployeeDeduction.query.filter_by(employee_id=employee.id).delete()

                # add new links
                for did in selected_ids:
                    db.session.add(EmployeeDeduction(employee_id=employee.id, deduction_id=did))

            elif benefit_type == "allowances":
                EmployeeAllowance.query.filter_by(employee_id=employee.id).delete()

                for aid in selected_ids:
                    db.session.add(EmployeeAllowance(employee_id=employee.id, allowance_id=aid))

            db.session.commit()
            success_message = f"{benefit_type.capitalize()} updated for {employee.first_name}!"

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

    return render_template(
        'payroll/admin/manage_deduction.html',
        employee=employee,
        all_items=all_items,
        selected_items=selected_items,
        benefit_type=benefit_type,
        success_message=success_message
    )
