from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

from hr_system.config import Config  # absolute import from your project root

# Extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config.from_object(Config)

    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["DEBUG"] = True


    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Register blueprints
    from hr_system.hr.routes.auth_routes import auth_bp
    from hr_system.hr.routes.hr_admin_routes import hr_admin_bp
    from hr_system.hr.routes.hr_officer_routes import hr_officer_bp
    from hr_system.hr.routes.dept_head_routes import dept_head_bp
    from hr_system.hr.routes.employee_routes import employee_bp
    from hr_system.hr.routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(hr_admin_bp, url_prefix="/hr/admin")
    app.register_blueprint(hr_officer_bp, url_prefix="/hr/officer")
    app.register_blueprint(dept_head_bp, url_prefix="/hr/dept_head")
    app.register_blueprint(employee_bp, url_prefix="/hr/employee")
    app.register_blueprint(api_bp, url_prefix="/api/hr")

    # Import models so migrations detect them
    from hr_system.hr.models import user, hr_models

    return app

# Flask-Login user loader
from hr_system.hr.models.user import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
