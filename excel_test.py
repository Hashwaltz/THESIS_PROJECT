from main_app import create_app  # adjust import to match your project
from flask_mail import Message
from main_app.extensions import db, mail

app = create_app()

with app.app_context():
    msg = Message(
        subject="Test Email",
        sender="natanielashleyrodelas@gmail.com",  # your Gmail
        recipients=["gianmariemmd06@gmail.com"],       # replace with your personal email
        body="This is a test email from Flask-Mail."
    )
    mail.send(msg)
    print("Test email sent successfully!")
