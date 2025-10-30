from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from main_app.extensions import db, login_manager


def create_app():

    

    app = Flask(__name__)
    # Load payroll config
    app.config.from_object("payroll_system.config.Config")

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "payroll_auth.login"

    # -------------------------------------
    # USER LOADER (shared HR User model)
    # -------------------------------------
    @login_manager.user_loader
    def load_user(user_id):
        from hr_system.hr.models.user import User
        return User.query.get(int(user_id))

    # -------------------------------------
    # BLUEPRINTS
    # -------------------------------------
    from payroll_system.payroll.routes.auth_routes import payroll_auth_bp
    from payroll_system.payroll.routes.payroll_admin_routes import payroll_admin_bp
    from payroll_system.payroll.routes.payroll_staff_routes import payroll_staff_bp
    from payroll_system.payroll.routes.employee_routes import payroll_employee_bp
    from payroll_system.payroll.routes.api_routes import payroll_api_bp

    app.register_blueprint(payroll_auth_bp, url_prefix="/payroll/auth")
    app.register_blueprint(payroll_admin_bp, url_prefix="/payroll/admin")
    app.register_blueprint(payroll_staff_bp, url_prefix="/payroll/staff")
    app.register_blueprint(payroll_employee_bp, url_prefix="/payroll/employee")
    app.register_blueprint(payroll_api_bp, url_prefix="/payroll/api")

    # -------------------------------------
    # ROOT ROUTE
    # -------------------------------------
    @app.route("/")
    def index():
        return redirect(url_for("payroll_auth.login"))

    return app
