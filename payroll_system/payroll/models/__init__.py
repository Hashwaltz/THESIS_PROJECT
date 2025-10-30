# payroll_system/payroll/models/__init__.py

from .payroll_models import (
    Payroll,
    Payslip,
    Deduction,
    Allowance,
    Tax,
    PayrollPeriod,
    EmployeeAllowance,
    EmployeeDeduction
)

# Import Employee separately from HR module
from hr_system.hr.models.hr_models import Employee
__all__ = [
    "Payroll",
    "Payslip",
    "Deduction",
    "Allowance",
    "Tax",
    "PayrollPeriod",
    "EmployeeAllowance",
    "EmployeeDeduction",
    "Employee"
]