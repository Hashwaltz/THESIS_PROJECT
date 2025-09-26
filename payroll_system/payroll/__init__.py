from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from main_app import db

# Initialize extensions
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("payroll_system.config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "payroll_auth.login"

    # -----------------------------
    # USER LOADER (FIXED HERE)
    # -----------------------------
    @login_manager.user_loader
    def load_user(user_id):
        # Import HR's User model here to avoid circular imports
        from hr_system.hr.models.user import User
        return User.query.get(int(user_id))  # ✅ real DB model, not PayrollUser

    # -----------------------------
    # BLUEPRINTS
    # -----------------------------
    from .routes.auth_routes import payroll_auth_bp
    from .routes.payroll_admin_routes import payroll_admin_bp
    from .routes.payroll_staff_routes import payroll_staff_bp
    from .routes.employee_routes import payroll_employee_bp
    from .routes.api_routes import payroll_api_bp

    app.register_blueprint(payroll_auth_bp, url_prefix="/auth")
    app.register_blueprint(payroll_admin_bp, url_prefix="/admin")
    app.register_blueprint(payroll_staff_bp, url_prefix="/staff")
    app.register_blueprint(payroll_employee_bp, url_prefix="/employee")
    app.register_blueprint(payroll_api_bp, url_prefix="/api")

    # -----------------------------
    # ROOT ROUTE
    # -----------------------------
    @app.route("/")
    def index():
        return redirect(url_for("payroll_auth.login"))

    return app
