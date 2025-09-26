from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateField, FloatField, IntegerField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange
from datetime import date

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me') 
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[
        ('admin', 'Payroll Admin'),
        ('staff', 'Payroll Staff'),
        ('employee', 'Employee')
    ], validators=[DataRequired()])
    submit = SubmitField('Register')

class PayrollPeriodForm(FlaskForm):
    period_name = StringField('Period Name', validators=[DataRequired(), Length(min=2, max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    pay_date = DateField('Pay Date', validators=[DataRequired()])
    submit = SubmitField('Create Period')

class PayrollForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    pay_period_start = DateField('Pay Period Start', validators=[DataRequired()])
    pay_period_end = DateField('Pay Period End', validators=[DataRequired()])
    basic_salary = FloatField('Basic Salary', validators=[DataRequired(), NumberRange(min=0)])
    overtime_hours = FloatField('Overtime Hours', validators=[Optional(), NumberRange(min=0)])
    overtime_pay = FloatField('Overtime Pay', validators=[Optional(), NumberRange(min=0)])
    holiday_pay = FloatField('Holiday Pay', validators=[Optional(), NumberRange(min=0)])
    night_differential = FloatField('Night Differential', validators=[Optional(), NumberRange(min=0)])
    other_deductions = FloatField('Other Deductions', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Calculate Payroll')

class PayslipForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    payroll_id = SelectField('Payroll Period', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Generate Payslip')

class DeductionForm(FlaskForm):
    name = StringField('Deduction Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    type = SelectField('Type', choices=[
        ('Fixed', 'Fixed Amount'),
        ('Percentage', 'Percentage'),
        ('Variable', 'Variable Amount')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[Optional(), NumberRange(min=0)])
    percentage = FloatField('Percentage', validators=[Optional(), NumberRange(min=0, max=100)])
    is_mandatory = BooleanField('Mandatory Deduction')
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save Deduction')

class AllowanceForm(FlaskForm):
    name = StringField('Allowance Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    type = SelectField('Type', choices=[
        ('Fixed', 'Fixed Amount'),
        ('Percentage', 'Percentage'),
        ('Variable', 'Variable Amount')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[Optional(), NumberRange(min=0)])
    percentage = FloatField('Percentage', validators=[Optional(), NumberRange(min=0, max=100)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save Allowance')

class TaxForm(FlaskForm):
    min_income = FloatField('Minimum Income', validators=[DataRequired(), NumberRange(min=0)])
    max_income = FloatField('Maximum Income', validators=[DataRequired(), NumberRange(min=0)])
    tax_rate = FloatField('Tax Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    fixed_amount = FloatField('Fixed Amount', validators=[Optional(), NumberRange(min=0)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save Tax Bracket')

class EmployeeSyncForm(FlaskForm):
    employee_id = StringField('Employee ID', validators=[DataRequired()])
    submit = SubmitField('Sync Employee')

class PayrollSummaryForm(FlaskForm):
    period_id = SelectField('Payroll Period', coerce=int, validators=[DataRequired()])
    department = SelectField('Department', validators=[Optional()])
    submit = SubmitField('Generate Summary')

class PayslipSearchForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[Optional()])
    period_start = DateField('Period Start', validators=[Optional()])
    period_end = DateField('Period End', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('', 'All'),
        ('Generated', 'Generated'),
        ('Sent', 'Sent'),
        ('Downloaded', 'Downloaded')
    ], validators=[Optional()])
    submit = SubmitField('Search')


