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

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'natanielashleyrodelas@gmail.com'
    MAIL_PASSWORD = 'jwrlqbebbzvvnzzs'

    # API timeout
    API_TIMEOUT = 30
