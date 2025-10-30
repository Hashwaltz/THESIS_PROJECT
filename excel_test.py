import pandas as pd
import re
from datetime import datetime, timedelta

xls_file = r"C:\Users\marriane\OneDrive\Desktop\attendance.xls"  # <-- change to your actual file

# --- Step 1: Read raw Excel file ---
try:
    df_raw = pd.read_excel(xls_file, engine="xlrd", header=None)
except Exception:
    df_raw = pd.read_excel(xls_file, engine="openpyxl", header=None)

df_raw = df_raw.fillna("").astype(str)

attendance_records = []
current_user = None
current_dept = None
attendance_date_start = None
attendance_date_end = None
current_day = None
daily_times = []

# --- Step 2: Parse text content ---
for i, row in df_raw.iterrows():
    text = " ".join(row)

    # Detect attendance date range
    date_range_match = re.search(r"Attendance date:(\d{4}-\d{2}-\d{2})~(\d{4}-\d{2}-\d{2})", text)
    if date_range_match:
        attendance_date_start = datetime.strptime(date_range_match.group(1), "%Y-%m-%d")
        attendance_date_end = datetime.strptime(date_range_match.group(2), "%Y-%m-%d")

    # Detect User ID and Department
    if "User ID:" in text:
        # Save previous user's last recorded day before switching
        if current_day and daily_times:
            attendance_records.append({
                "User ID": current_user,
                "Department": current_dept,
                "Day": int(current_day),
                "Time In": daily_times[0],
                "Time Out": daily_times[-1] if len(daily_times) > 1 else daily_times[0]
            })
        # Reset
        current_day = None
        daily_times = []
        user_match = re.search(r"User ID:\s*(\d+)", text)
        dept_match = re.search(r"Department:\s*(.+)", text)
        if user_match:
            current_user = user_match.group(1)
        if dept_match:
            current_dept = dept_match.group(1).strip()
        continue

    # Detect day number (1, 2, 3, ...)
    day_match = re.match(r"^\s*(\d+)\s*$", text)
    if day_match:
        if current_day and daily_times:
            attendance_records.append({
                "User ID": current_user,
                "Department": current_dept,
                "Day": int(current_day),
                "Time In": daily_times[0],
                "Time Out": daily_times[-1] if len(daily_times) > 1 else daily_times[0]
            })
        current_day = day_match.group(1)
        daily_times = []
        continue

    # Detect times (HH:MM)
    time_match = re.findall(r"\b\d{1,2}:\d{2}\b", text)
    if time_match:
        daily_times.extend(time_match)

# Save last group for final user
if current_day and daily_times:
    attendance_records.append({
        "User ID": current_user,
        "Department": current_dept,
        "Day": int(current_day),
        "Time In": daily_times[0],
        "Time Out": daily_times[-1] if len(daily_times) > 1 else daily_times[0]
    })

# --- Step 3: Build DataFrame ---
df = pd.DataFrame(attendance_records)

# Ensure Day column is int
df["Day"] = df["Day"].astype(int)

# Determine all possible days in report
if attendance_date_start and attendance_date_end:
    total_days = (attendance_date_end - attendance_date_start).days + 1
    all_days = list(range(1, total_days + 1))
else:
    all_days = sorted(df["Day"].unique())

# --- Step 4: Fill absences ---
final_records = []
users = sorted(df["User ID"].unique())

for user in users:
    user_rows = df[df["User ID"] == user]
    dept = user_rows["Department"].iloc[0] if not user_rows.empty else None

    for day in all_days:
        match = user_rows[user_rows["Day"] == day]
        if not match.empty:
            final_records.append({
                "User ID": user,
                "Department": dept,
                "Day": day,
                "Time In": match["Time In"].iloc[0],
                "Time Out": match["Time Out"].iloc[0],
            })
        else:
            final_records.append({
                "User ID": user,
                "Department": dept,
                "Day": day,
                "Time In": "ABSENT",
                "Time Out": "ABSENT",
            })

# --- Step 5: Final Output ---
final_df = pd.DataFrame(final_records)
final_df = final_df.sort_values(by=["User ID", "Day"])

print("\n✅ Complete Attendance Table:")
print(final_df)

final_df.to_csv("attendance_complete.csv", index=False)
print("\n💾 Saved to attendance_complete.csv")
