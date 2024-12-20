#this file contains some other functions that are used in the project

import re
import math
import smtplib
from email.mime.text import MIMEText
import random

def custom_hash(value): #custom hashing function for storing sensitive information
    plaintext = value
    hash = 0
    for i in range(len(plaintext)):
        hash += math.sin(ord(plaintext[i])/81) * i * (ord(plaintext[i + 1]) if i + 1 < len(plaintext) else 1) / len(plaintext)
        # adds the sine of the ascii values (divided by 81 so that the values are between 0 and 1 and dont repeat),
        # multiplies it by the position of the character in the string, then multiplies it by the ascii value of the
        # next character (if applicable) to ensure that the hash is as unique as possible
        # it is then divided by the length of the string to ensure that the hash is not too large
    return hash

def linkify(message): #turns messages into html links, so that #123 becomes a clickable link to /books/123
    if "#" not in message:
        return message
    
    newmessage = re.sub(r'#(\d+)', r'<a href="/books/\1">#\1</a>', message)
    return newmessage

def recoverpassword(email): #sends a recovery email to the user
    websiteemail = "tudoralt2007@gmail.com" #app login for a burner email of mine for testing purposes
    password = "boxw snpc mglr hcoe"

    code = random.randint(100000, 999999) #generate recovery code

    #form email
    subject = "Your Verification Code"
    body = f"Your verification code is: {code}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = websiteemail
    msg['To'] = email

    #send email to user
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(websiteemail, password)
            server.sendmail(websiteemail, email, msg.as_string())

    return str(code) #return code so that it can be used to verify the user's identity