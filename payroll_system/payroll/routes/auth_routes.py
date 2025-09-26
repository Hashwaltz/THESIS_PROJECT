from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from payroll_system.payroll.forms import LoginForm, RegistrationForm
from payroll_system.payroll import db
from hr_system.hr.models.user import User  
from datetime import datetime

payroll_auth_bp = Blueprint(
    "payroll_auth",
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

# -----------------------------
# INDEX -> redirect to login
# -----------------------------
@payroll_auth_bp.route("/")
def index():
    return redirect(url_for("payroll_auth.login"))

# -----------------------------
# LOGIN
# -----------------------------
@payroll_auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        # Already logged in: redirect by role
        return redirect_by_role(current_user.role)

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()

        if not user:
            flash('Invalid email or password.', 'error')
            return render_template('auth/login.html', form=form)

        # Check password (plain-text OR hashed)
        if check_password_hash(user.password, form.password.data) or user.password.strip() == form.password.data.strip():
            if not user.active:
                flash('Your account has been deactivated. Please contact administrator.', 'error')
                return render_template('auth/login.html', form=form)

            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Redirect based on role
            return redirect_by_role(user.role)
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html', form=form)


# -----------------------------
# ROLE REDIRECT HELPER
# -----------------------------
def redirect_by_role(role: str):
    role = role.lower()
    if role == "admin":
        return redirect(url_for("payroll_admin.dashboard"))
    elif role in ["officer", "dept_head"]:   # both treated as staff
        return redirect(url_for("payroll_staff.dashboard"))
    elif role == "employee":
        return redirect(url_for("payroll_employee.dashboard"))
    else:
        flash("Role not recognized.", "danger")
        return redirect(url_for("payroll_auth.login"))


# -----------------------------
# LOGOUT
# -----------------------------
@payroll_auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("payroll_auth.login"))

# -----------------------------
# REGISTER
# -----------------------------
@payroll_auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("payroll_employee.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return render_template("auth/register.html", form=form)

        # Create new Payroll user (shared user table from HR)
        user = User(
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data,
        )

        try:
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("payroll_auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "danger")

    return render_template("auth/register.html", form=form)

# -----------------------------
# PROFILE
# -----------------------------
@payroll_auth_bp.route("/profile")
@login_required
def profile():
    return render_template("auth/profile.html", user=current_user)

# -----------------------------
# CHANGE PASSWORD
# -----------------------------
@payroll_auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not check_password_hash(current_user.password, current_password):
            flash("Current password is incorrect.", "danger")
            return render_template("auth/change_password.html")

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return render_template("auth/change_password.html")

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "danger")
            return render_template("auth/change_password.html")

        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("Password changed successfully.", "success")
        return redirect(url_for("payroll_auth.profile"))

    return render_template("auth/change_password.html")
