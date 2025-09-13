from hr_system.hr import create_app, db
from hr_system.hr.models.hr_models import Department  # adjust import if needed
from datetime import datetime

# Create app context
app = create_app()
app.app_context().push()

# Municipal departments/offices
departments = [
    "Office of the Mayor",
    "Office of the Vice Mayor",
    "Sangguniang Bayan",
    "Office of the Municipal Treasurer",
    "Municipal Planning and Development Office (MPDO)",
    "Municipal Budget Office",
    "Municipal Assessor's Office",
    "Municipal Accounting Office",
    "Municipal Civil Registrar",
    "Municipal Health Office",
    "Municipal Social Welfare and Development Office",
    "Municipal Engineer's Office",
    "Municipal Legal Office",
    "Municipal Agriculture Office",
    "Municipal Environment and Natural Resources Office (MENRO)",
    "Municipal Local Government Operations Office (MLGOO)"
]

# Insert departments into the database
for dept_name in departments:
    existing = Department.query.filter_by(name=dept_name).first()
    if not existing:
        dept = Department(
            name=dept_name,
            description=f"{dept_name} Department",
            created_at=datetime.utcnow()
        )
        db.session.add(dept)

db.session.commit()
print("Municipal departments added successfully!")
