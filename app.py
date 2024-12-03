from database import *
from functools import wraps
import hashlib
from flask import Flask, render_template, url_for, request, redirect, session

app = Flask(__name__)
app.secret_key = "bookloop-is-very-cool"

def hash(value):
    return str(hashlib.sha256(value.encode()).hexdigest())

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'username' not in session or 'password_hash' not in session:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/')
@login_required
def home():  
    return render_template('index.html', username = session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login(): 
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        password_hash = hash(password)

        if checklogin(username, password_hash):
            if remember:
                session['username'] = username
                session['password_hash'] = password_hash
                app.permanent_session_lifetime = 7*60*60*24
                session.permanent = True
            return redirect(url_for('home'))

    return render_template('login.html')
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        password_hash = hash(password)
        
        try:
            adduser(username, email, password_hash)
            return redirect(url_for('login'))
        except:
            return "username or email already exists"
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/booksearch', methods=['GET', 'POST'])
@login_required
def booksearch():
    return render_template('booksearch.html')

@app.route('/addbook', methods=['GET', 'POST'])
@login_required
def addbook():
    return render_template('addbook.html')

if __name__ == '__main__':
    app.run(debug=True)