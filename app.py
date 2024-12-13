from database import *
from misc import *
from functools import wraps
from PIL import Image
import time
from flask import Flask, render_template, url_for, request, redirect, session

app = Flask(__name__)
app.secret_key = "bookloop-is-very-cool"
app.permanent_session_lifetime = 7*60*60*24



def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'username' not in session or 'password_hash' not in session:
            return redirect(url_for('login'))
        elif not checklogin(session['username'], session['password_hash']):
            session.clear()
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

            session.clear()
            session['username'] = username
            session['password_hash'] = password_hash

            if remember:
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

@app.route('/books', defaults={'bookid':None}, methods=['GET', 'POST'])
@app.route('/books/<int:bookid>')
@login_required
def books(bookid):
    if bookid is not None:

        if bookid not in [i[0] for i in cursor.execute("SELECT id FROM books")]:
            return "book not found"

        book = cursor.execute("SELECT * FROM books WHERE id = ?", (bookid,)).fetchone()
        bookinfo = {'id':book[0], 'title':book[1], 'author':book[2], 'description':book[3], 'owner':cursor.execute("SELECT username FROM users WHERE id = ?", (book[4],)).fetchone()[0], 'tags':[i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (bookid,))]}
        tags = [i[0] for i in cursor.execute("")]
        pastowners = [{'name':i[0]} for i in cursor.execute("SELECT users.username FROM users, transactions WHERE transactions.bookid = ? AND transactions.sellerid = users.id ORDER BY transactions.time DESC", (bookid,)).fetchall()]

        return render_template('bookinfo.html', book=bookinfo, pastowners=pastowners)



    booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'tags':[j[0] for j in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (i[0],))]} for i in cursor.execute("SELECT * FROM books WHERE currentowner != ?", (str(getuserid(session['username'], )))).fetchall()]

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

        ownerid = getuserid(session['username'])

        addbook(title, author, description, ownerid, tags)

        bookid = cursor.execute("SELECT id FROM books WHERE title = ? AND author = ? AND description = ? AND currentowner = ? ORDER BY id DESC", (title, author, description, ownerid)).fetchone()[0]

        filepath = f"static/photos/{bookid}.jpeg"
        image = Image.open(photo)
        image = image.convert('RGB')
        image.save(filepath, 'JPEG')

        return redirect(url_for('home'))
        
    return render_template('createlisting.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags").fetchall()])
    
@app.route('/chats', defaults={'chatid': None})
@app.route('/chats/<int:chatid>', methods=['GET', 'POST'])
@login_required
def chats(chatid):
    if chatid is not None:
        if session['username'] not in [i[0] for i in cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid = users.id", (chatid,)).fetchall()]:
            return "you do not have access to this chat"

        name = cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid = users.id AND users.username != ?", (chatid, session['username'])).fetchone()[0]
        messages = [{'sender':cursor.execute("SELECT username FROM users WHERE id = ?", (i[0],)).fetchone()[0], 'time':i[1], 'message':linkify(i[2])} for i in cursor.execute("SELECT messages.sender, messages.time, messages.message FROM messages WHERE messages.chat = ?", (chatid,)).fetchall()]

        if request.method == 'POST':
            message = request.form.get('message')
            sendmessage(getuserid(session['username']), chatid, message)
            return redirect(url_for('chats', chatid=chatid))

        return render_template('chat.html', chatid=chatid, name=name, messages=messages)

    userid = getuserid(session['username'])
    chatids = [i[0] for i in cursor.execute("SELECT DISTINCT chats.chatid FROM chats, messages WHERE chats.userid = ? AND chats.chatid = messages.chat ORDER BY (SELECT MAX(time) FROM messages WHERE messages.chat = chats.chatid) DESC", (userid,)).fetchall()]
    chatinfo = [{'id':i, 'name':cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid != ? AND chats.userid = users.id", (i, userid)).fetchone()[0], 'lastactivity':cursor.execute("SELECT (messages.time) FROM messages WHERE messages.chat = ?", (i,)).fetchone()[0]} for i in chatids]

    return render_template('chats.html', chats=chatinfo)

@app.route('/message/<string:user>', defaults={'bookid': None}, methods=['GET', 'POST'])
@app.route('/message/<string:user>/<int:bookid>', methods=['GET', 'POST'])
@login_required
def message(user, bookid):
    userid = cursor.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()[0]
    myid = getuserid(session['username'])
    if request.method == 'POST':
        message = request.form.get('message')
        if not chatbetween(userid, myid):
            createchat(userid, myid)
        newchatid = chatbetween(userid, myid)
        if bookid is not None:
            message = f"message regarding book {cursor.execute('SELECT title FROM books WHERE id = ?', (bookid,)).fetchone()[0]} #{bookid}: " + message
        sendmessage(myid, newchatid, message)

        return redirect(url_for('chats', chatid=newchatid))
    
    if userid == myid:
        return "you cannot talk to yourself"
    
    return render_template('message.html', user=user, bookid=bookid)

@app.route('/updatechat/<int:chatid>', methods=['GET', 'POST'])
@login_required
def updatechat(chatid):
    messages = [{'sender':cursor.execute("SELECT username FROM users WHERE id = ?", (i[0],)).fetchone()[0], 'time':i[1], 'message':linkify(i[2])} for i in cursor.execute("SELECT messages.sender, messages.time, messages.message FROM messages WHERE messages.chat = ?", (chatid,)).fetchall()]
    messages_html = ''.join([f"<p><strong>{msg['sender']}</strong> [{msg['time']}]: {msg['message']}</p>"for msg in messages])

    return messages_html

@app.route('/transfer/<string:user>', methods=['GET', 'POST'])
@login_required
def transfer(user):
    userid = cursor.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()[0]
    myid = getuserid(session['username'])

    mybooks = [{'title':i[1]} for i in cursor.execute("SELECT * FROM books WHERE currentowner = ?", (myid,)).fetchall()]

    if request.method == 'POST':
        transferedbooknames = request.form.getlist('books')
        for i in transferedbooknames:
            id = cursor.execute("SELECT id FROM books WHERE title = ?", (i,)).fetchone()[0]
            transferbook(id, myid, userid)

        return redirect(url_for('chats', chatid=chatbetween(userid, myid)))

    return render_template('transfer.html', user=user, mybooks=mybooks)

@app.route('/mybooks', methods=['GET', 'POST'])
@login_required
def mybooks():
    myid = getuserid(session['username'])
    booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'tags':[j[0] for j in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (i[0],))]} for i in cursor.execute("SELECT * FROM books WHERE currentowner = ?", (myid,)).fetchall()]

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

    return render_template('mybooks.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags")], books=booklist)

@app.route('/editbook/<int:bookid>', methods=['GET', 'POST'])
@login_required
def editbookpage(bookid):
    myid = getuserid(session['username'])

    if cursor.execute("SELECT currentowner FROM books WHERE id = ?", (bookid,)).fetchone()[0] != myid:
        return "you do not own this book"
    
    bookdata = cursor.execute("SELECT title, author, description FROM books WHERE id = ?", (bookid,)).fetchone()
    book = {'id':bookid, 'title':bookdata[0], 'author':bookdata[1], 'description':bookdata[2]}
    tags = [i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (bookid,)).fetchall()]
    availabletags = [i[0] for i in cursor.execute("SELECT tagname FROM tags").fetchall()]

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        tags = request.form.getlist('tags')
        photo = request.files['photo']

        editbook(bookid, title, author, description, tags)

        if photo:
            filepath = f"static/photos/{bookid}.jpeg"
            image = Image.open(photo)
            image = image.convert('RGB')
            image.save(filepath, 'JPEG')

        return redirect(url_for('mybooks'))
    
    return render_template('editbook.html', book=book, availabletags = availabletags, tags = tags)

@app.route('/deletebook/<int:bookid>')
@login_required
def deletebookpage(bookid):
    myid = getuserid(session['username'])

    if cursor.execute("SELECT currentowner FROM books WHERE id = ?", (bookid,)).fetchone()[0] != myid:
        return "you do not own this book"
    
    deletebook(bookid)
    return redirect(url_for('mybooks'))

@app.route('/forgotpassword', defaults={'email': None}, methods=['GET', 'POST'])
@app.route('/forgotpassword/<string:email>', methods=['GET', 'POST'])
def forgotpassword(email):
    if email is not None:
        if 'code' not in session or session['code'] is None:
            session['code'] = hash(recoverpassword(email))
            session['recoverycodetimestamp'] = time.time()

        else:
            if time.time() - session['recoverycodetimestamp'] > 300:
                session['code'] = None
                return redirect(url_for('forgotpassword', email=email))

        if request.method == 'POST':
            insertedcode = request.form.get('code')
            newpassword = request.form.get('password')

            if hash(insertedcode) == session['code']:
                changepassword(email, newpassword)
                session.clear()
                return redirect(url_for('login'))
            return "incorrect code" 
        
        return render_template('changepassword.html', email=email)

    if request.method == 'POST':
        email = request.form.get('email')
        return redirect(url_for('forgotpassword', email=email))
    
    return render_template('forgotpassword.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)