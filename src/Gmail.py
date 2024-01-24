import smtplib
import temp_bingx
from firebase_admin import db
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(subject):
    sender_email = db.reference("/google/email").get()
    receiver_email = sender_email
    app_password = db.reference("/google/app_pw").get()

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    text = "whatwant is a good man."
    html = f"<html><body><p>{text}</p></body></html>"
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, message.as_string())


if __name__ == "__main__":

    subject = "This is a lucky email from Python"

    send_email(subject)