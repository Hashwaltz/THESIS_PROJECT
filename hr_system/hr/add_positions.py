from hr_system.hr import create_app, db
from hr_system.hr.models.hr_models import Department, Position
from datetime import datetime

# Create app context
app = create_app()
app.app_context().push()

# Map of departments to positions
department_positions = {
    "Office of the Mayor": [
        "Mayor",
        "Executive Assistant",
        "Administrative Assistant",
        "Secretary"
    ],
    "Office of the Vice Mayor": [
        "Vice Mayor",
        "Legislative Staff",
        "Secretary"
    ],
    "Sangguniang Bayan": [
        "Councilor",
        "Legislative Assistant",
        "Secretary"
    ],
    "Office of the Municipal Treasurer": [
        "Municipal Treasurer",
        "Cashier",
        "Collection Officer"
    ],
    "Municipal Planning and Development Office (MPDO)": [
        "Urban Planner",
        "Development Officer",
        "Technical Staff"
    ],
    "Municipal Budget Office": [
        "Budget Officer",
        "Financial Analyst",
        "Clerk"
    ],
    "Municipal Assessor's Office": [
        "Municipal Assessor",
        "Appraiser",
        "Assessment Clerk"
    ],
    "Municipal Accounting Office": [
        "Accountant",
        "Auditor",
        "Accounting Clerk"
    ],
    "Municipal Civil Registrar": [
        "Civil Registrar",
        "Registrar Staff"
    ],
    "Municipal Health Office": [
        "Municipal Health Officer",
        "Doctor",
        "Nurse",
        "Midwife",
        "Medical Technologist"
    ],
    "Municipal Social Welfare and Development Office": [
        "Social Worker",
        "Program Coordinator",
        "Support Staff"
    ],
    "Municipal Engineer's Office": [
        "Municipal Engineer",
        "Civil Engineer",
        "Technical Assistant",
        "Construction Worker"
    ],
    "Municipal Legal Office": [
        "Municipal Legal Officer",
        "Legal Staff"
    ],
    "Municipal Agriculture Office": [
        "Agriculturist",
        "Extension Worker",
        "Support Staff"
    ],
    "Municipal Environment and Natural Resources Office (MENRO)": [
        "Environmental Officer",
        "Forester",
        "Technical Staff"
    ],
    "Municipal Local Government Operations Office (MLGOO)": [
        "Administrative Officer",
        "Support Staff"
    ]
}

# Insert positions into the database
for dept_name, positions in department_positions.items():
    dept = Department.query.filter_by(name=dept_name).first()
    if dept:
        for pos_name in positions:
            existing = Position.query.filter_by(name=pos_name, department_id=dept.id).first()
            if not existing:
                position = Position(
                    name=pos_name,
                    description=f"{pos_name} in {dept_name}",
                    department_id=dept.id
                )
                db.session.add(position)

db.session.commit()
print("Positions added successfully!")
