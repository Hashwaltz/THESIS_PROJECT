import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///norzagaray_hr_payroll.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # HR System Configuration
    HR_SYSTEM_URL = 'http://localhost:5000'
    
    # Payroll System Configuration
    PAYROLL_SYSTEM_URL = 'http://localhost:5000'
    
    # API Configuration
    API_TIMEOUT = 30

