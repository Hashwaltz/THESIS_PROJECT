from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from ..forms import LoginForm, RegistrationForm
from .. import db
from ..models.user import User
from ..models.hr_models import Employee, Attendance
from ..utils import admin_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hr_admin.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # Plain-text password check
        if user and user.password == form.password.data:
            if not user.active:
                flash('Your account has been deactivated. Please contact administrator.', 'error')
                return render_template('auth/login.html', form=form)

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Role-based redirect
            role = user.role.lower()
            if role == 'admin':
                return redirect(url_for('hr_admin.dashboard'))
            elif role == 'officer':
                return redirect(url_for('hr_officer.dashboard'))
            elif role == 'dept_head':
                return redirect(url_for('dept_head.dashboard'))
            else:
                return redirect(url_for('employee.dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('hr_admin.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered.', 'error')
            return render_template('auth/register.html', form=form)
        
        user = User(
            email=form.email.data,
            password=form.password.data,  # plain-text password
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data,
            department=form.department.data,
            position=form.position.data
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Plain-text password check
        if current_user.password != current_password:
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long.', 'error')
            return render_template('auth/change_password.html')
        
        current_user.password = new_password
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')
