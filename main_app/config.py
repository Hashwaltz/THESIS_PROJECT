import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance')),
        'hr_and_payroll.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # HR System Configuration
    HR_SYSTEM_URL = 'http://localhost:5000'

    # Payroll System Configuration
    PAYROLL_SYSTEM_URL = 'http://localhost:5000'

    # API Configuration
    API_TIMEOUT = 30

    # Email Configuration (Gmail SMTP)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'natanielashleyrodelas@gmail.com'  # your Gmail address
    MAIL_PASSWORD = 'bdsi joih safg xedl'  