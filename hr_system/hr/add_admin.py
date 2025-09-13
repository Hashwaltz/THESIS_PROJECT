from hr_system.hr import create_app, db
from hr_system.hr.models.user import User
from datetime import datetime

app = create_app()

with app.app_context():
    # Example: Add two admin users
    admin1 = User(
        email="admin1@example.com",
        password="hashed_password1",
        first_name="Admin",
        last_name="One",
        role="admin",
        active=True
    )

    admin2 = User(
        email="admin2@example.com",
        password="hashed_password2",
        first_name="Admin",
        last_name="Two",
        role="admin",
        active=True
    )

    db.session.add(admin1)
    db.session.add(admin2)
    db.session.commit()

    print("Two admin users added successfully!")
