from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("payroll_system.config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "payroll_auth.login"

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from payroll.models.user import PayrollUser
        return PayrollUser.query.get(int(user_id))

    # Blueprints
    from payroll.routes.auth_routes import payroll_auth_bp
    from payroll.routes.payroll_admin_routes import payroll_admin_bp
    from payroll.routes.payroll_staff_routes import payroll_staff_bp
    from payroll.routes.employee_routes import payroll_employee_bp
    from payroll.routes.api_routes import payroll_api_bp

    app.register_blueprint(payroll_auth_bp, url_prefix="/auth")
    app.register_blueprint(payroll_admin_bp, url_prefix="/admin")
    app.register_blueprint(payroll_staff_bp, url_prefix="/staff")
    app.register_blueprint(payroll_employee_bp, url_prefix="/employee")
    app.register_blueprint(payroll_api_bp, url_prefix="/api")

    return app


