from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from ..forms import LoginForm, RegistrationForm
from .. import db
from ..models.user import User
from ..models.hr_models import Employee, Attendance
from ..utils import admin_required
import os



from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from ..forms import LoginForm, RegistrationForm
from .. import db
from ..models.user import User
from ..models.hr_models import Employee, Attendance
from ..utils import admin_required
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "hr_static")


hr_auth_bp = Blueprint(
    "hr_auth",
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/hr/static"
)

@hr_auth_bp.route('/')
def index():
    return redirect(url_for('hr_auth.login'))


@hr_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Already logged in: redirect by role
        role = current_user.role.lower()
        if role == 'admin':
            return redirect(url_for('hr_admin.hr_dashboard'))   
        elif role == 'officer':
            return redirect(url_for('officer.hr_dashboard'))
        elif role == 'dept_head':
            return redirect(url_for('dept_head.dashboard'))
        elif role == 'employee':
            return redirect(url_for('employee.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        print("Form email:", form.email.data)
        print("User fetched:", user)

        if user:
            print("User password in DB:", user.password)
            print("Entered password:", form.password.data)
        else:
            flash('Invalid email or password.', 'error')
            return render_template('hr_auth/hr_login.html', form=form)

        # Plain-text password check
        if user.password.strip() == form.password.data.strip():
            if not user.active:
                flash('Your account has been deactivated. Please contact administrator.', 'error')
                return render_template('hr_auth/hr_login.html', form=form)

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Role-based redirect
            role = user.role.lower()
            if role == 'admin':
                return redirect(url_for('hr_admin.hr_dashboard'))
            elif role == 'officer':
                return redirect(url_for('officer.hr_dashboard'))
            elif role == 'dept_head':
                return redirect(url_for('dept_head.dashboard'))
            elif role == 'employee':
                return redirect(url_for('employee.dashboard'))

        else:
            flash('Invalid email or password.', 'error')

    return render_template('hr_auth/hr_login.html', form=form)


@hr_auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('hr_auth.login'))

# ----------------- EDIT PROFILE ROUTE -----------------
@hr_auth_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user

    if request.method == 'POST':
        # Get form inputs safely
        user.email = request.form.get('email')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')

        # Only update password if a new one was entered
        password = request.form.get('password')
        if password and password.strip():
            user.password = password

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')

        return redirect(url_for('hr_auth.edit_profile'))

    return render_template('hr_auth/profile.html', user=user)

