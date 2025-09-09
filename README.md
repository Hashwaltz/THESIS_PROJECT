# Norzagaray HR & Payroll System

A comprehensive integrated Human Resources and Payroll Management System built with Flask, designed for the Municipality of Norzagaray.

## 🚀 Features

### HR System
- **Employee Management**: Complete employee lifecycle management
- **Attendance Tracking**: Record and monitor employee attendance
- **Leave Management**: Handle leave requests and approvals
- **Department Management**: Organize employees by departments
- **Role-Based Access Control**: Admin, HR Officer, Department Head, Employee roles
- **User Management**: Secure user authentication and authorization

### Payroll System
- **Payroll Processing**: Automated salary calculations
- **Payslip Generation**: Generate and distribute payslips
- **Deduction Management**: SSS, PhilHealth, Pag-IBIG, Tax calculations
- **Allowance Management**: Various allowance types and calculations
- **Payroll Periods**: Bi-monthly payroll processing
- **Reports & Analytics**: Comprehensive payroll reporting

### Integration Features
- **Real-time Data Sync**: Seamless integration between HR and Payroll systems
- **API Integration**: RESTful APIs for data exchange
- **Unified Dashboard**: Single entry point for both systems
- **Cross-System Authentication**: Shared user management

## 🏗️ Architecture

```
norzagaray_hr_payroll/
│
├── main_app/                           # Unified entry point
│   ├── __init__.py
│   ├── run.py
│   ├── config.py
│   └── templates/
│       └── index.html
│
├── hr_system/                          # HR System
│   ├── hr/
│   │   ├── models/                     # Database models
│   │   ├── routes/                     # API endpoints
│   │   ├── templates/                  # HTML templates
│   │   ├── static/                     # CSS/JS assets
│   │   ├── forms.py                    # WTForms
│   │   └── utils.py                    # Utility functions
│   ├── config.py
│   ├── requirements.txt
│   └── run.py
│
├── payroll_system/                     # Payroll System
│   ├── payroll/
│   │   ├── models/                     # Database models
│   │   ├── routes/                     # API endpoints
│   │   ├── templates/                  # HTML templates
│   │   ├── static/                     # CSS/JS assets
│   │   ├── forms.py                    # WTForms
│   │   └── utils.py                    # Utility functions
│   ├── config.py
│   ├── requirements.txt
│   └── run.py
│
└── docs/                              # Documentation
    ├── architecture_diagram.png
    └── api_contracts.md
```

## 🛠️ Technology Stack

- **Backend**: Flask 2.3.3
- **Database**: SQLite (development), PostgreSQL (production)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF, WTForms
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Icons**: Font Awesome 6
- **API**: RESTful APIs with JSON responses

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd norzagaray_hr_payroll
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

#### For Main Application
```bash
cd main_app
pip install -r ../hr_system/requirements.txt
pip install -r ../payroll_system/requirements.txt
```

#### For HR System (Standalone)
```bash
cd hr_system
pip install -r requirements.txt
```

#### For Payroll System (Standalone)
```bash
cd payroll_system
pip install -r requirements.txt
```

### 4. Database Setup
```bash
# From main_app directory
python run.py
# This will create the database and tables automatically
```

### 5. Run the Application

#### Integrated System (Recommended)
```bash
cd main_app
python run.py
```

#### Individual Systems
```bash
# HR System
cd hr_system
python run.py

# Payroll System
cd payroll_system
python run.py
```

## 🌐 Access the Application

- **Main Dashboard**: http://localhost:5000
- **HR System**: http://localhost:5000/hr
- **Payroll System**: http://localhost:5000/payroll

## 👥 User Roles

### HR System Roles
- **HR Admin**: Full system access, employee management, system configuration
- **HR Officer**: Employee management, attendance, leave processing
- **Department Head**: Department-specific employee management
- **Employee**: View own records, request leaves, view attendance

### Payroll System Roles
- **Payroll Admin**: Full payroll system access, configuration
- **Payroll Staff**: Payroll processing, payslip generation
- **Employee**: View payslips, payroll history

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///norzagaray_hr_payroll.db
HR_SYSTEM_URL=http://localhost:5001
PAYROLL_SYSTEM_URL=http://localhost:5002
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Database Configuration
The system uses SQLite by default. For production, configure PostgreSQL:

```python
# In config.py
SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/norzagaray_hr_payroll'
```

## 📊 API Endpoints

### HR System API
- `GET /api/hr/employees` - Get all employees
- `GET /api/hr/employees/{id}` - Get specific employee
- `POST /api/hr/employees` - Create employee
- `PUT /api/hr/employees/{id}` - Update employee
- `GET /api/hr/attendance` - Get attendance records
- `GET /api/hr/leaves` - Get leave records

### Payroll System API
- `GET /api/payroll/employees` - Get all employees
- `GET /api/payroll/employees/{id}` - Get specific employee
- `POST /api/payroll/employees/sync` - Sync employees from HR
- `GET /api/payroll/payroll` - Get payroll records
- `GET /api/payroll/payslips` - Get payslip records
- `GET /api/payroll/periods` - Get payroll periods

## 🔐 Security Features

- **Password Hashing**: Secure password storage using Werkzeug
- **Session Management**: Flask-Login for session handling
- **CSRF Protection**: Flask-WTF CSRF tokens
- **Role-Based Access**: Granular permission system
- **Input Validation**: Form validation and sanitization

## 📈 Payroll Calculations

### Deductions
- **SSS**: Based on salary brackets
- **PhilHealth**: 3% of basic salary
- **Pag-IBIG**: 2% of basic salary
- **Tax**: Progressive tax calculation based on BIR rates

### Allowances
- **Overtime Pay**: 25% premium on hourly rate
- **Holiday Pay**: Double pay for holidays
- **Night Differential**: 10% premium for night work

## 🧪 Testing

### Run Tests
```bash
# Unit tests (to be implemented)
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/
```

### Test Data
The system includes sample data for testing:
- Sample employees
- Test payroll periods
- Sample deductions and allowances

## 📝 Usage Examples

### Creating an Employee
1. Login as HR Admin
2. Navigate to Employees → Add Employee
3. Fill in employee details
4. Save employee record

### Processing Payroll
1. Login as Payroll Admin
2. Create payroll period
3. Sync employees from HR system
4. Process payroll for all employees
5. Generate payslips

### Requesting Leave
1. Login as Employee
2. Navigate to Leaves → Request Leave
3. Fill in leave details
4. Submit for approval

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check if database file exists
ls -la *.db

# Recreate database
rm *.db
python run.py
```

#### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### Port Already in Use
```bash
# Kill process using port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
python run.py --port 5001
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Authors

- **Development Team** - *Initial work* - [Your Name]

## 🙏 Acknowledgments

- Flask community for the excellent framework
- Bootstrap team for the responsive UI components
- Font Awesome for the beautiful icons
- All contributors and testers

## 📞 Support

For support and questions:
- Email: support@norzagaray.gov.ph
- Phone: +63-XXX-XXX-XXXX
- Documentation: [Link to detailed docs]

## 🔄 Version History

- **v1.0.0** - Initial release with basic HR and Payroll functionality
- **v1.1.0** - Added API integration and improved UI
- **v1.2.0** - Enhanced security and reporting features

---

**Note**: This system is designed specifically for the Municipality of Norzagaray. Please ensure compliance with local labor laws and regulations when implementing in production.


