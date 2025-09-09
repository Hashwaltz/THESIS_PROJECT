from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, date
from ..models.user import User
from ..models.hr_models import Employee, Attendance
from ..forms import EmployeeForm
from ..utils import admin_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/employees')
@login_required
def get_employees():
    """Get all employees for API consumption"""
    try:
        employees = Employee.query.filter_by(active=True).all()
        employee_data = []

        for emp in employees:
            employee_data.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'middle_name': emp.middle_name,
                'email': emp.email,
                'phone': emp.phone,
                'department': emp.department,
                'position': emp.position,
                'salary': emp.salary,
                'date_hired': emp.date_hired.isoformat() if emp.date_hired else None,
                'date_of_birth': emp.date_of_birth.isoformat() if emp.date_of_birth else None,
                'gender': emp.gender,
                'marital_status': emp.marital_status,
                'active': emp.active,
                'created_at': emp.created_at.isoformat(),
                'updated_at': emp.updated_at.isoformat()
            })

        return jsonify({
            'success': True,
            'data': employee_data,
            'count': len(employee_data)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# --- Keep the rest of your API routes unchanged ---
# Just ensure that all imports use relative paths:
# from ..models.user, from ..models.hr_models, from ..utils, from .. import db
