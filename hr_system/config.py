import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hr-secret-key-here'

    # Single shared database for HR and Payroll
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance')),
        'hr_and_payroll.db'
    )

    # No need for SQLALCHEMY_BINDS since we are using a single DB
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 
        'uploads', 
        'images'
    )
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Email configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # API timeout
    API_TIMEOUT = 30
