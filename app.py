from database import *
from functools import wraps
import hashlib
from PIL import Image
from flask import Flask, render_template, url_for, request, redirect, session

app = Flask(__name__)
app.secret_key = "bookloop-is-very-cool"

def hash(value):
    return str(hashlib.sha256(value.encode()).hexdigest())

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'username' not in session or 'password_hash' not in session or not checklogin(session['username'], session['password_hash']):
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

    booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'tags':[j[0] for j in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (i[0],))]} for i in cursor.execute("SELECT * FROM books").fetchall()]

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        tags = request.form.getlist('tags')

        query = "SELECT * FROM books WHERE 1=1"

        if title:
            query += f" AND title LIKE '%{title}%'"
        
        if author:
            query += f" AND author LIKE '%{author}%'"

        if tags:
            for i in tags:
                id = cursor.execute("SELECT id FROM tags WHERE tagname = ?", (i,)).fetchone()[0]
                query += f" AND id IN (SELECT bookid FROM booktags WHERE tagid = {id})"

        booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'description':i[3]} for i in cursor.execute(query).fetchall()]

    return render_template('booksearch.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags")], books=booklist)

@app.route('/createlisting', methods=['GET', 'POST'])
@login_required
def createlisting():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        tags = request.form.getlist('tags')
        photo = request.files['photo']

        ownerid = cursor.execute("SELECT id FROM users WHERE username = ?", (session['username'],)).fetchone()[0]

        addbook(title, author, description, ownerid, tags)

        bookid = cursor.execute("SELECT id FROM books WHERE title = ? AND author = ? AND description = ? AND currentowner = ? ORDER BY id DESC", (title, author, description, ownerid)).fetchone()[0]

        filepath = f"static/photos/{bookid}.jpeg"
        image = Image.open(photo)
        image = image.convert('RGB')
        image.save(filepath, 'JPEG')

        return redirect(url_for('home'))
        
    return render_template('createlisting.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags").fetchall()])

@app.route('/bookinfo/<int:bookid>')
@login_required
def bookinfo(bookid):
    book = cursor.execute("SELECT * FROM books WHERE id = ?", (bookid,)).fetchone()
    tags = [i[0] for i in cursor.execute("")]

    return render_template('bookinfo.html', book=book, tags=tags)

if __name__ == '__main__':
    app.run(debug=True, port=8080)