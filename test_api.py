from main_app.extensions import db
from main_app import create_app
from hr_system.hr.models.hr_models import Employee, Attendance
from hr_system.hr.models.user import User
from datetime import datetime, date, timedelta, time
import random

app = create_app()  # create your Flask app instance


def random_time(start_hour=7, end_hour=8):
    """Return a random time between start_hour:00 and end_hour:59."""
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    return time(hour, minute)


def random_late_time(start_hour=8, end_hour=8):
    """Return a random late time between 08:01 and 08:15."""
    hour = start_hour
    minute = random.randint(1, 15)
    return time(hour, minute)


def generate_attendance_jan_to_nov():
    with app.app_context():  # push app context for database access
        employees = Employee.query.all()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 12, 30)
        delta = timedelta(days=1)

        # Philippine holidays
        holidays = [
            date(2025, 1, 1),
            date(2025, 2, 25),
            date(2025, 3, 31),
            date(2025, 4, 9),
            date(2025, 5, 1),
            date(2025, 6, 12),
            date(2025, 8, 21),
            date(2025, 8, 25),
            date(2025, 11, 1),
            date(2025, 11, 2),
        ]

        for emp in employees:
            current_date = start_date
            attendance_dates = []

            while current_date <= end_date:
                if current_date.weekday() < 5 and current_date not in holidays:
                    attendance_dates.append(current_date)
                current_date += delta

            total_days = len(attendance_dates)
            late_count = max(5, total_days // 20)
            absent_count = max(5, total_days // 25)

            late_dates = random.sample(attendance_dates, min(late_count, total_days))
            remaining_dates = [d for d in attendance_dates if d not in late_dates]
            absent_dates = random.sample(remaining_dates, min(absent_count, len(remaining_dates)))

            for day in attendance_dates:
                if day in late_dates:
                    status = "Late"
                    time_in = random_late_time()
                    time_out = time(17, 0)
                    remarks = f"Late - Time In: {time_in.strftime('%I:%M %p')}"
                elif day in absent_dates:
                    status = "Absent"
                    # Randomly decide if completely absent or partial absence
                    if random.choice([True, False]):
                        # Completely absent
                        time_in = None
                        time_out = None
                        remarks = "Absent"
                    else:
                        # Partial absence (late arrival or early leave)
                        time_in = random_time(9, 11)
                        time_out = time(17, 0)
                        remarks = f"Absent - Partial (Time In: {time_in.strftime('%I:%M %p')})"
                else:
                    status = "Present"
                    time_in = random_time()
                    time_out = time(17, 0)
                    remarks = None

                attendance = Attendance(
                    employee_id=emp.id,
                    date=day,
                    time_in=time_in,
                    time_out=time_out,
                    status=status,
                    remarks=remarks
                )
                db.session.add(attendance)

        db.session.commit()
        print("✅ Attendance records (Jan–Nov 2025, realistic absents & late) added successfully!")


if __name__ == "__main__":
    generate_attendance_jan_to_nov()
