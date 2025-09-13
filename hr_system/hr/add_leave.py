from hr_system.hr import create_app, db
from hr_system.hr.models.hr_models import LeaveType

leave_types = [
    ("Vacation Leave", "Leave for rest, recreation, or personal matters"),
    ("Sick Leave", "Leave for illness, injury, or medical needs"),
    ("Emergency Leave", "For urgent, unforeseen matters"),
    ("Maternity Leave", "105 days maternity leave for female employees"),
    ("Paternity Leave", "7 days leave for male employees after spouse gives birth"),
    ("Parental Leave", "7 days leave for solo parents"),
    ("Bereavement Leave", "Leave for death of immediate family member"),
    ("Special Leave for Women", "Gynecological surgery leave (RA 9710)"),
    ("Study Leave", "For exams, review, or study purposes"),
    ("Service Incentive Leave", "5 days leave per year (private sector)"),
    ("Official Business", "Employee is away for official duties/training"),
    ("Leave Without Pay", "Leave without salary if no leave credits left"),
]

app = create_app()

with app.app_context():
    for name, desc in leave_types:
        if not LeaveType.query.filter_by(name=name).first():
            db.session.add(LeaveType(name=name, description=desc))
    db.session.commit()
    print("✅ Leave types inserted successfully!")
