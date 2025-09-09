# API Contracts Documentation

This document describes the API contracts between the HR and Payroll systems in the Norzagaray HR & Payroll Management System.

## Overview

The systems communicate through RESTful APIs using JSON format. All API endpoints return responses in the following format:

```json
{
    "success": true/false,
    "data": {...},
    "error": "error message if success is false",
    "count": "number of items (for list endpoints)"
}
```

## Authentication

All API endpoints require authentication. Include the session cookie or API key in requests.

## HR System API Endpoints

### Base URL
- Development: `http://localhost:5001`
- Production: `https://hr.norzagaray.gov.ph`

### Employee Management

#### Get All Employees
```http
GET /api/hr/employees
```

**Query Parameters:**
- `page` (optional): Page number for pagination
- `limit` (optional): Number of items per page
- `department` (optional): Filter by department
- `active` (optional): Filter by active status

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "employee_id": "IT-0001",
            "first_name": "John",
            "last_name": "Doe",
            "middle_name": "Smith",
            "email": "john.doe@norzagaray.gov.ph",
            "phone": "+63-XXX-XXX-XXXX",
            "department": "IT",
            "position": "Software Developer",
            "salary": 50000.00,
            "date_hired": "2024-01-15",
            "active": true,
            "created_at": "2024-01-15T08:00:00Z",
            "updated_at": "2024-01-15T08:00:00Z"
        }
    ],
    "count": 1
}
```

#### Get Employee by ID
```http
GET /api/hr/employees/{employee_id}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "employee_id": "IT-0001",
        "first_name": "John",
        "last_name": "Doe",
        "middle_name": "Smith",
        "email": "john.doe@norzagaray.gov.ph",
        "phone": "+63-XXX-XXX-XXXX",
        "address": "123 Main St, Norzagaray, Bulacan",
        "department": "IT",
        "position": "Software Developer",
        "salary": 50000.00,
        "date_hired": "2024-01-15",
        "date_of_birth": "1990-05-15",
        "gender": "Male",
        "marital_status": "Single",
        "emergency_contact": "Jane Doe",
        "emergency_phone": "+63-XXX-XXX-XXXX",
        "active": true,
        "created_at": "2024-01-15T08:00:00Z",
        "updated_at": "2024-01-15T08:00:00Z"
    }
}
```

#### Create Employee
```http
POST /api/hr/employees
```

**Request Body:**
```json
{
    "employee_id": "IT-0002",
    "first_name": "Jane",
    "last_name": "Smith",
    "middle_name": "Marie",
    "email": "jane.smith@norzagaray.gov.ph",
    "phone": "+63-XXX-XXX-XXXX",
    "address": "456 Oak St, Norzagaray, Bulacan",
    "department": "IT",
    "position": "System Administrator",
    "salary": 45000.00,
    "date_hired": "2024-02-01",
    "date_of_birth": "1988-03-20",
    "gender": "Female",
    "marital_status": "Married",
    "emergency_contact": "John Smith",
    "emergency_phone": "+63-XXX-XXX-XXXX"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 2,
        "employee_id": "IT-0002",
        "message": "Employee created successfully"
    }
}
```

#### Update Employee
```http
PUT /api/hr/employees/{employee_id}
```

**Request Body:**
```json
{
    "first_name": "Jane",
    "last_name": "Smith-Jones",
    "salary": 50000.00,
    "active": true
}
```

**Response:**
```json
{
    "success": true,
    "message": "Employee updated successfully"
}
```

### Attendance Management

#### Get Attendance Records
```http
GET /api/hr/attendance
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee
- `start_date` (optional): Filter from date (YYYY-MM-DD)
- `end_date` (optional): Filter to date (YYYY-MM-DD)
- `status` (optional): Filter by status (Present, Absent, Late, Half Day)

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "employee_id": 1,
            "date": "2024-01-15",
            "time_in": "08:00:00",
            "time_out": "17:00:00",
            "status": "Present",
            "remarks": "On time",
            "created_at": "2024-01-15T08:00:00Z"
        }
    ],
    "count": 1
}
```

### Leave Management

#### Get Leave Records
```http
GET /api/hr/leaves
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee
- `status` (optional): Filter by status (Pending, Approved, Rejected)
- `leave_type` (optional): Filter by leave type

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "employee_id": 1,
            "leave_type": "Sick",
            "start_date": "2024-01-20",
            "end_date": "2024-01-22",
            "days_requested": 3,
            "reason": "Flu symptoms",
            "status": "Approved",
            "approved_by": 1,
            "approved_at": "2024-01-19T10:00:00Z",
            "comments": "Approved by HR Manager",
            "created_at": "2024-01-19T09:00:00Z",
            "updated_at": "2024-01-19T10:00:00Z"
        }
    ],
    "count": 1
}
```

## Payroll System API Endpoints

### Base URL
- Development: `http://localhost:5002`
- Production: `https://payroll.norzagaray.gov.ph`

### Employee Management

#### Get All Employees
```http
GET /api/payroll/employees
```

**Response:** Same format as HR system employee endpoint

#### Sync Employees from HR
```http
POST /api/payroll/employees/sync
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully synced 25 employees",
    "synced_count": 25
}
```

### Payroll Management

#### Get Payroll Records
```http
GET /api/payroll/payroll
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee
- `period_id` (optional): Filter by payroll period
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "employee_id": 1,
            "pay_period_start": "2024-01-01",
            "pay_period_end": "2024-01-15",
            "basic_salary": 50000.00,
            "overtime_hours": 8.0,
            "overtime_pay": 2500.00,
            "holiday_pay": 0.00,
            "night_differential": 0.00,
            "gross_pay": 52500.00,
            "sss_contribution": 500.00,
            "philhealth_contribution": 1500.00,
            "pagibig_contribution": 1000.00,
            "tax_withheld": 5250.00,
            "other_deductions": 0.00,
            "total_deductions": 8250.00,
            "net_pay": 44250.00,
            "status": "Processed",
            "created_at": "2024-01-16T08:00:00Z",
            "updated_at": "2024-01-16T08:00:00Z"
        }
    ],
    "count": 1
}
```

### Payslip Management

#### Get Payslips
```http
GET /api/payroll/payslips
```

**Query Parameters:**
- `employee_id` (optional): Filter by employee
- `status` (optional): Filter by status (Generated, Sent, Downloaded)
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "employee_id": 1,
            "payslip_number": "PS2024010001",
            "pay_period_start": "2024-01-01",
            "pay_period_end": "2024-01-15",
            "basic_salary": 50000.00,
            "overtime_pay": 2500.00,
            "holiday_pay": 0.00,
            "night_differential": 0.00,
            "allowances": 0.00,
            "gross_pay": 52500.00,
            "sss_contribution": 500.00,
            "philhealth_contribution": 1500.00,
            "pagibig_contribution": 1000.00,
            "tax_withheld": 5250.00,
            "other_deductions": 0.00,
            "total_deductions": 8250.00,
            "net_pay": 44250.00,
            "status": "Generated",
            "generated_at": "2024-01-16T08:00:00Z"
        }
    ],
    "count": 1
}
```

### Payroll Periods

#### Get Payroll Periods
```http
GET /api/payroll/periods
```

**Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "period_name": "January 2024 - First Half",
            "start_date": "2024-01-01",
            "end_date": "2024-01-15",
            "pay_date": "2024-01-20",
            "status": "Open",
            "created_at": "2024-01-01T08:00:00Z"
        }
    ],
    "count": 1
}
```

## Error Responses

### 400 Bad Request
```json
{
    "success": false,
    "error": "Missing required field: employee_id"
}
```

### 401 Unauthorized
```json
{
    "success": false,
    "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
    "success": false,
    "error": "Admin access required"
}
```

### 404 Not Found
```json
{
    "success": false,
    "error": "Employee not found"
}
```

### 500 Internal Server Error
```json
{
    "success": false,
    "error": "Internal server error"
}
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per IP
- **Headers**: 
  - `X-RateLimit-Limit`: Request limit per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets

## Data Validation

### Employee Data
- `employee_id`: Required, unique, 3-20 characters
- `first_name`: Required, 2-100 characters
- `last_name`: Required, 2-100 characters
- `email`: Required, valid email format, unique
- `phone`: Optional, valid phone format
- `department`: Required, valid department name
- `position`: Required, 2-100 characters
- `salary`: Optional, positive number
- `date_hired`: Required, valid date

### Payroll Data
- `basic_salary`: Required, positive number
- `overtime_hours`: Optional, non-negative number
- `gross_pay`: Required, positive number
- `net_pay`: Required, positive number

## Security Considerations

1. **Authentication**: All endpoints require valid session or API key
2. **Authorization**: Role-based access control
3. **Input Validation**: All inputs are validated and sanitized
4. **CSRF Protection**: CSRF tokens for state-changing operations
5. **Rate Limiting**: Prevents abuse and ensures fair usage
6. **Data Encryption**: Sensitive data is encrypted in transit and at rest

## Testing

### Test Endpoints
- Health Check: `GET /api/hr/health` and `GET /api/payroll/health`
- Response format validation
- Error handling verification

### Sample Test Data
```json
{
    "test_employee": {
        "employee_id": "TEST-001",
        "first_name": "Test",
        "last_name": "User",
        "email": "test@norzagaray.gov.ph",
        "department": "IT",
        "position": "Test Position",
        "salary": 30000.00,
        "date_hired": "2024-01-01"
    }
}
```

## Versioning

- **Current Version**: v1.0
- **Version Header**: `API-Version: 1.0`
- **Backward Compatibility**: Maintained for at least 2 versions

## Support

For API support and questions:
- Email: api-support@norzagaray.gov.ph
- Documentation: [Link to detailed API docs]
- Status Page: [Link to API status page]


