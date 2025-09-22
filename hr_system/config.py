import os

# Base directory of the project (where app.py/run.py is)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# Upload folder inside static/uploads/images
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure upload folder exists


class Config:
    # Secret key for session and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hr-secret-key-here'

    # 🔹 Instance folder for databases (moved inside the class)
    INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
    print("INSTANCE_PATH from Config:", INSTANCE_PATH)

    os.makedirs(INSTANCE_PATH, exist_ok=True)  # Ensure the folder exists

    # Database configuration (main HR system database)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(INSTANCE_PATH, 'hr_system.db')

    # Bind for Payroll database
    SQLALCHEMY_BINDS = {
        'payroll': 'sqlite:///' + os.path.join(INSTANCE_PATH, 'payroll_system.db')
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Email configuration for notifications
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # API configuration
    API_TIMEOUT = 30
