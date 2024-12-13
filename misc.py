import re
import hashlib
import smtplib
from email.mime.text import MIMEText
import random

def hash(value):
    return str(hashlib.sha256(value.encode()).hexdigest())

def linkify(message):
    if "#" not in message:
        return message
    
    newmessage = re.sub(r'#(\d+)', r'<a href="/books/\1">#\1</a>', message)
    return newmessage

def recoverpassword(email):
    websiteemail = "tudoralt2007@gmail.com"
    password = "boxw snpc mglr hcoe"

    code = random.randint(100000, 999999)

    subject = "Your Verification Code"
    body = f"Your verification code is: {code}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = websiteemail
    msg['To'] = email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(websiteemail, password)
            server.sendmail(websiteemail, email, msg.as_string())

    return str(code)