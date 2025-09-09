import os

# Base directory of the project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Instance folder for databases
INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_PATH, exist_ok=True)  # Ensure the folder exists

# Upload folder inside static
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure upload folder exists

class Config:
    # Secret key for session and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hr-secret-key-here'

    # Database configuration
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
