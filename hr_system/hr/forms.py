from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, DateField, TimeField, IntegerField, FloatField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange
from datetime import date

# ------------------------
# Authentication Forms
# ------------------------

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
        ('admin', 'HR Admin'),
        ('officer', 'HR Officer'),
        ('dept_head', 'Department Head'),
        ('employee', 'Employee')
    ], validators=[DataRequired()])
    department = StringField('Department', validators=[Optional(), Length(max=100)])
    position = StringField('Position', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Register')

# ------------------------
# Employee Forms
# ------------------------

class EmployeeForm(FlaskForm):
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(min=3, max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=100)])
    middle_name = StringField('Middle Name', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional()])
    department = SelectField('Department', choices=[
        ('IT', 'Information Technology'),
        ('HR', 'Human Resources'),
        ('Finance', 'Finance'),
        ('Operations', 'Operations'),
        ('Marketing', 'Marketing'),
        ('Sales', 'Sales'),
        ('Admin', 'Administration')
    ], validators=[DataRequired()])
    position = StringField('Position', validators=[DataRequired(), Length(max=100)])
    salary = FloatField('Salary', validators=[Optional(), NumberRange(min=0)])
    date_hired = DateField('Date Hired', validators=[DataRequired()], default=date.today)
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ], validators=[Optional()])
    marital_status = SelectField('Marital Status', choices=[
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed')
    ], validators=[Optional()])
    emergency_contact = StringField('Emergency Contact', validators=[Optional(), Length(max=100)])
    emergency_phone = StringField('Emergency Phone', validators=[Optional(), Length(max=20)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save Employee')

# ------------------------
# Attendance Forms
# ------------------------

class AttendanceForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    time_in = TimeField('Time In', validators=[Optional()])
    time_out = TimeField('Time Out', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
        ('Half Day', 'Half Day')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Remarks', validators=[Optional()])
    submit = SubmitField('Record Attendance')

# ------------------------
# Leave Forms
# ------------------------

class LeaveForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    leave_type = SelectField('Leave Type', choices=[
        ('Sick', 'Sick Leave'),
        ('Vacation', 'Vacation Leave'),
        ('Personal', 'Personal Leave'),
        ('Emergency', 'Emergency Leave'),
        ('Maternity', 'Maternity Leave'),
        ('Paternity', 'Paternity Leave')
    ], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    days_requested = IntegerField('Days Requested', validators=[DataRequired(), NumberRange(min=1)])
    reason = TextAreaField('Reason', validators=[DataRequired()])
    submit = SubmitField('Submit Leave Request')

class LeaveApprovalForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('Approved', 'Approve'),
        ('Rejected', 'Reject')
    ], validators=[DataRequired()])
    comments = TextAreaField('Comments', validators=[Optional()])
    submit = SubmitField('Update Status')

# ------------------------
# Department Forms
# ------------------------

class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    head_id = SelectField('Department Head', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Department')
