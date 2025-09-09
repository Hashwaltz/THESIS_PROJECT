from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///norzagaray_hr_payroll.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from hr_system.hr.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from hr_system.hr import create_app as create_hr_app
    from payroll_system.payroll import create_app as create_payroll_app
    
    # Create sub-apps
    hr_app = create_hr_app()
    payroll_app = create_payroll_app()
    
    # Register HR routes
    from hr_system.hr.routes.auth_routes import auth_bp
    from hr_system.hr.routes.hr_admin_routes import hr_admin_bp
    from hr_system.hr.routes.hr_officer_routes import hr_officer_bp
    from hr_system.hr.routes.dept_head_routes import dept_head_bp
    from hr_system.hr.routes.employee_routes import employee_bp
    from hr_system.hr.routes.api_routes import api_bp
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(hr_admin_bp, url_prefix="/hr/admin")
    app.register_blueprint(hr_officer_bp, url_prefix="/hr/officer")
    app.register_blueprint(dept_head_bp, url_prefix="/hr/dept_head")
    app.register_blueprint(employee_bp, url_prefix="/hr/employee")
    app.register_blueprint(api_bp, url_prefix="/api/hr")
    
    # Register Payroll routes
    from payroll_system.payroll.routes.auth_routes import payroll_auth_bp
    from payroll_system.payroll.routes.payroll_admin_routes import payroll_admin_bp
    from payroll_system.payroll.routes.payroll_staff_routes import payroll_staff_bp
    from payroll_system.payroll.routes.employee_routes import payroll_employee_bp
    from payroll_system.payroll.routes.api_routes import payroll_api_bp
    
    app.register_blueprint(payroll_auth_bp, url_prefix="/payroll/auth")
    app.register_blueprint(payroll_admin_bp, url_prefix="/payroll/admin")
    app.register_blueprint(payroll_staff_bp, url_prefix="/payroll/staff")
    app.register_blueprint(payroll_employee_bp, url_prefix="/payroll/employee")
    app.register_blueprint(payroll_api_bp, url_prefix="/api/payroll")
    
    # Main dashboard route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/hr')
    def hr_dashboard():
        return redirect(url_for('auth.login'))
    
    @app.route('/payroll')
    def payroll_dashboard():
        return redirect(url_for('payroll_auth.login'))
    
    return app

