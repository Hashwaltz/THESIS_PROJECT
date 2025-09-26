from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from main_app.extensions import db, login_manager, migrate

# Import shared User model
from hr_system.hr.models.user import User  

# Import all HR models so migrations know they exist
import hr_system.hr.models.hr_models  

# Import Payroll models
import payroll_system.payroll.models.payroll_models  

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hr_and_payroll.db'  # shared DB
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key'

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)  # Now Alembic sees all models
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # ===== User loader for Flask-Login =====
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ===== Register HR Blueprints =====
    from hr_system.hr.routes.auth_routes import auth_bp
    from hr_system.hr.routes.hr_admin_routes import hr_admin_bp
    from hr_system.hr.routes.hr_officer_routes import hr_officer_bp
    from hr_system.hr.routes.dept_head_routes import dept_head_bp
    from hr_system.hr.routes.employee_routes import employee_bp
    from hr_system.hr.routes.api_routes import api_bp
    app.register_blueprint(auth_bp, url_prefix='/hr/auth')
    app.register_blueprint(hr_admin_bp, url_prefix='/hr/admin')
    app.register_blueprint(hr_officer_bp, url_prefix="/hr/officer")
    app.register_blueprint(dept_head_bp, url_prefix="/hr/dept_head")
    app.register_blueprint(employee_bp, url_prefix="/hr/employee")
    app.register_blueprint(api_bp, url_prefix="/api")


    # ===== Register Payroll Blueprints =====
    from payroll_system.payroll.routes.auth_routes import payroll_auth_bp
    from payroll_system.payroll.routes.payroll_admin_routes import payroll_admin_bp
    app.register_blueprint(payroll_auth_bp, url_prefix='/payroll/auth')
    app.register_blueprint(payroll_admin_bp, url_prefix='/payroll/admin')

    # ===== Landing page =====
    @app.route('/')
    def index():
        return render_template('index.html')

    return app
