import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'payroll-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///hr_and_payroll.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Payroll System specific configurations
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # HR System API configuration
    HR_SYSTEM_URL = os.environ.get('HR_SYSTEM_URL') or 'http://localhost:5000'
    HR_API_TIMEOUT = 30
    
    # Payroll calculations
    TAX_RATE = 0.20  # 20% tax rate
    SSS_RATE = 0.11  # 11% SSS rate
    PHILHEALTH_RATE = 0.03  # 3% PhilHealth rate
    PAGIBIG_RATE = 0.02  # 2% Pag-IBIG rate
    
    # Email configuration (for payslip notifications)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
