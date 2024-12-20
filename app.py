from database import *
from misc import *
from functools import wraps
from PIL import Image
import time
from flask import Flask, render_template, url_for, request, redirect, session

app = Flask(__name__)
#prevents anyone from changing the session data on the client side
app.secret_key = "bookloop-is-very-cool"
#session data is stored for 7 days when "remember me" is checked
app.permanent_session_lifetime = 7*60*60*24


#this function can be added to any page that requires login
#it automatically redirects to the login page if the user is not logged in
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
    if request.method == 'POST': #receive user inputs
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'

        #hash the password before storing it anywhere
        password_hash = custom_hash(password)
        
        if checklogin(username, password_hash): #check if login is valid

            session.clear()
            session['username'] = username #store user data in session
            session['password_hash'] = password_hash

            if remember: #if remember is ticked the session data will be stored even if the browser restarts
                session.permanent = True

        return redirect(url_for('home')) #redirect to home page after login

    return render_template('login.html')
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST': #receive user inputs
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        password_hash = custom_hash(password) #password is hashed so its not stored as plaintext
        
        try:
            adduser(username, email, password_hash) #add user to data base
            return redirect(url_for('login'))
        except:
            return "username or email already exists"
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear() #clear session data
    return redirect(url_for('login'))


@app.route('/books', defaults={'bookid':None}, methods=['GET', 'POST']) #if /books is accessed without a bookid, it will show all books
@app.route('/books/<int:bookid>') #if /books/<bookid> is accessed, it will show the book with that id
@login_required
def books(bookid):
    if bookid is not None: #if there is an id

        #check if book exists
        if bookid not in [i[0] for i in cursor.execute("SELECT id FROM books")]:
            return "book not found"

        #fetch the book data from the database and add it to a dictionary
        book = cursor.execute("SELECT * FROM books WHERE id = ?", (bookid,)).fetchone()

        bookinfo = {'id':book[0], 'title':book[1], 'author':book[2], 'description':book[3], 'owner':cursor.execute("SELECT username FROM users WHERE id = ?", (book[4],)).fetchone()[0], 'tags':[i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (bookid,))]}

        pastowners = [{'name':i[0]} for i in cursor.execute("SELECT users.username FROM users, transactions WHERE transactions.bookid = ? AND transactions.sellerid = users.id ORDER BY transactions.time DESC", (bookid,)).fetchall()]

        return render_template('bookinfo.html', book=bookinfo, pastowners=pastowners)

    #if no bookid is specified show all books

    #example query that fetches all books that arent owned
    query = "SELECT * FROM books WHERE currentowner != ?" #dont show books that the user owns

    if request.method == 'POST': #if the user has search parameters
        title = request.form.get('title')
        author = request.form.get('author')
        tags = request.form.getlist('tags')

        #add those parameters to the query
        if title:
            query += f" AND title LIKE '%{title}%'"
        
        if author:
            query += f" AND author LIKE '%{author}%'"

        if tags:
            for i in tags:
                id = cursor.execute("SELECT id FROM tags WHERE tagname = ?", (i,)).fetchone()[0]
                query += f" AND id IN (SELECT bookid FROM booktags WHERE tagid = {id})"

    #search for books using the query
    booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'description':i[3], 'tags':[i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (i[0],))]} for i in cursor.execute(query, (str(getuserid(session['username'], )))).fetchall()]

    return render_template('booksearch.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags")], books=booklist)


@app.route('/createlisting', methods=['GET', 'POST'])
@login_required
def createlisting():
    if request.method == 'POST': #get book data
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        tags = request.form.getlist('tags')
        photo = request.files['photo']

        ownerid = getuserid(session['username'])

        addbook(title, author, description, ownerid, tags) #add book to database

        #fetch the book id
        bookid = cursor.execute("SELECT id FROM books WHERE title = ? AND author = ? AND description = ? AND currentowner = ? ORDER BY id DESC", (title, author, description, ownerid)).fetchone()[0]

        #store the books photo as <bookid>.jpeg
        filepath = f"static/photos/{bookid}.jpeg"
        image = Image.open(photo)
        image = image.convert('RGB')
        image.save(filepath, 'JPEG')

        return redirect(url_for('home'))
        
    return render_template('createlisting.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags").fetchall()])


@app.route('/chats', defaults={'chatid': None}) #if /chats is accessed without a chatid, it will show all chats for that user
@app.route('/chats/<int:chatid>', methods=['GET', 'POST']) #if /chats/<chatid> is accessed, it will show the chat with that id
@login_required
def chats(chatid):
    if chatid is not None: #if there is a chatid

        #check if user has access to that chat
        if session['username'] not in [i[0] for i in cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid = users.id", (chatid,)).fetchall()]:
            return "you do not have access to this chat"

        #display chat name by fetching the name of the other user
        name = cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid = users.id AND users.username != ?", (chatid, session['username'])).fetchone()[0]

        #fetch message data and add it to a dictionary
        messages = [{'sender':cursor.execute("SELECT username FROM users WHERE id = ?", (i[0],)).fetchone()[0], 'time':i[1], 'message':linkify(i[2])} for i in cursor.execute("SELECT messages.sender, messages.time, messages.message FROM messages WHERE messages.chat = ?", (chatid,)).fetchall()]

        if request.method == 'POST': #if user sends a message
            message = request.form.get('message')
            sendmessage(getuserid(session['username']), chatid, message) #add message to database
            return redirect(url_for('chats', chatid=chatid))

        return render_template('chat.html', chatid=chatid, name=name, messages=messages)

    #if no chatid is specified show all chats
    userid = getuserid(session['username'])
    #fetch all chat ids (sorted by last activity)

    chatids = [i[0] for i in cursor.execute("SELECT DISTINCT chats.chatid FROM chats, messages WHERE chats.userid = ? AND chats.chatid = messages.chat ORDER BY (SELECT MAX(time) FROM messages WHERE messages.chat = chats.chatid) DESC", (userid,)).fetchall()]

    #for each id fetch the data
    chatinfo = [{'id':i, 'name':cursor.execute("SELECT users.username FROM users, chats WHERE chats.chatid = ? AND chats.userid != ? AND chats.userid = users.id", (i, userid)).fetchone()[0], 'lastactivity':cursor.execute("SELECT (messages.time) FROM messages WHERE messages.chat = ?", (i,)).fetchone()[0]} for i in chatids]

    return render_template('chats.html', chats=chatinfo)


@app.route('/message/<string:user>', defaults={'bookid': None}, methods=['GET', 'POST']) #if /message/<user> is accessed without a bookid, you just send a normal message
@app.route('/message/<string:user>/<int:bookid>', methods=['GET', 'POST']) #if there is a bookid, the message will specify what book its about
@login_required
def message(user, bookid):

    userid = cursor.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()[0]
    myid = getuserid(session['username'])

    if request.method == 'POST':
        message = request.form.get('message')

        if not chatbetween(userid, myid): #if theres no chat between the two users, create one
            createchat(userid, myid)
        chatid = chatbetween(userid, myid) #fetch the chat id

        if bookid is not None: #if there is a bookid, add it to the message
            message = f"message regarding book {cursor.execute('SELECT title FROM books WHERE id = ?', (bookid,)).fetchone()[0]} #{bookid}: " + message
        
        sendmessage(myid, chatid, message) #add message to database

        return redirect(url_for('chats', chatid=chatid))
    
    if userid == myid: #if user tries to message themselves
        return "you cannot talk to yourself"
    
    return render_template('message.html', user=user, bookid=bookid)


@app.route('/updatechat/<int:chatid>', methods=['GET', 'POST']) #this function is for updating the chat without refreshing the page
@login_required
def updatechat(chatid):

    #fetches messages and returns them in html format
    messages = [{'sender':cursor.execute("SELECT username FROM users WHERE id = ?", (i[0],)).fetchone()[0], 'time':i[1], 'message':linkify(i[2])} for i in cursor.execute("SELECT messages.sender, messages.time, messages.message FROM messages WHERE messages.chat = ?", (chatid,)).fetchall()]

    messages_html = ''.join([f"<p><strong>{msg['sender']}</strong> [{msg['time']}]: {msg['message']}</p>"for msg in messages])

    #this doesnt display a new page, but returns data to the page that requested it
    return messages_html


@app.route('/transfer/<string:user>', methods=['GET', 'POST']) #this page is for transferring an owned book to another user
@login_required
def transfer(user):
    userid = cursor.execute("SELECT id FROM users WHERE username = ?", (user,)).fetchone()[0]
    myid = getuserid(session['username'])

    #fetch owned books
    mybooks = [{'title':i[1]} for i in cursor.execute("SELECT * FROM books WHERE currentowner = ?", (myid,)).fetchall()]

    if request.method == 'POST': #once the user selects one or multiple books to transfer
        transferedbooknames = request.form.getlist('books')

        for i in transferedbooknames:
            id = cursor.execute("SELECT id FROM books WHERE title = ?", (i,)).fetchone()[0]
            #transfer each book to the other user
            transferbook(id, myid, userid)

        return redirect(url_for('chats', chatid=chatbetween(userid, myid))) #return to chat with the other user

    return render_template('transfer.html', user=user, mybooks=mybooks)


@app.route('/mybooks', methods=['GET', 'POST']) #page for viewing owned books
@login_required
def mybooks():
    myid = getuserid(session['username'])
    #example query that fetches all books owned
    query = "SELECT * FROM books WHERE currentowner = ?" #only show books that the user owns

    if request.method == 'POST': #if the user has search parameters
        title = request.form.get('title')
        author = request.form.get('author')
        tags = request.form.getlist('tags')

        #add those parameters to the query
        if title:
            query += f" AND title LIKE '%{title}%'"
        
        if author:
            query += f" AND author LIKE '%{author}%'"

        if tags:
            for i in tags:
                id = cursor.execute("SELECT id FROM tags WHERE tagname = ?", (i,)).fetchone()[0]
                query += f" AND id IN (SELECT bookid FROM booktags WHERE tagid = {id})"

    #search for books using the query
    booklist = [{'id':i[0], 'title':i[1], 'author':i[2], 'description':i[3], 'tags':[i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (i[0],))]} for i in cursor.execute(query, (str(myid), )).fetchall()]

    return render_template('mybooks.html', availabletags=[i[0] for i in cursor.execute("SELECT tagname FROM tags")], books=booklist)


@app.route('/editbook/<int:bookid>', methods=['GET', 'POST']) #page for editing a book
@login_required
def editbookpage(bookid):
    myid = getuserid(session['username'])

    if cursor.execute("SELECT currentowner FROM books WHERE id = ?", (bookid,)).fetchone()[0] != myid: #check if user owns the book
        return "you do not own this book"
    
    #fetch book data and add it to a dictionary
    bookdata = cursor.execute("SELECT title, author, description FROM books WHERE id = ?", (bookid,)).fetchone()

    book = {'id':bookid, 'title':bookdata[0], 'author':bookdata[1], 'description':bookdata[2]}

    tags = [i[0] for i in cursor.execute("SELECT tags.tagname FROM tags, booktags WHERE booktags.bookid = ? AND booktags.tagid = tags.id", (bookid,)).fetchall()]
    
    availabletags = [i[0] for i in cursor.execute("SELECT tagname FROM tags").fetchall()]

    if request.method == 'POST': #when user inputs new data
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        tags = request.form.getlist('tags')
        photo = request.files['photo']

        editbook(bookid, title, author, description, tags) #edit book data

        if photo: #upload new photo if applicable
            filepath = f"static/photos/{bookid}.jpeg"
            image = Image.open(photo)
            image = image.convert('RGB')
            image.save(filepath, 'JPEG')

        return redirect(url_for('mybooks'))
    
    return render_template('editbook.html', book=book, availabletags = availabletags, tags = tags)


@app.route('/deletebook/<int:bookid>') #doesnt display a new page. This is a function called upon by a button
@login_required
def deletebookpage(bookid):
    myid = getuserid(session['username'])

    if cursor.execute("SELECT currentowner FROM books WHERE id = ?", (bookid,)).fetchone()[0] != myid: #check if user owns the book
        return "you do not own this book"
    
    deletebook(bookid) #delete book
    return redirect(url_for('mybooks'))


@app.route('/forgotpassword', defaults={'email': None}, methods=['GET', 'POST']) #page for inputing an email
@app.route('/forgotpassword/<string:email>', methods=['GET', 'POST']) #once email is inputed, user is sent a code to change password
def forgotpassword(email):
    if email is not None: #if email is inputed
        if 'code' not in session or session['code'] is None: #if a code hasnt been generated send one
            session['code'] = custom_hash(recoverpassword(email)) #stored as hash to prevent user from reading cookie data
            session['recoverycodetimestamp'] = time.time()
            session['email'] = email

        else:
            if time.time() - session['recoverycodetimestamp'] > 300: #if the code has expired clear session and try again (valid for 5 min)
                session['code'] = None
                session['email'] = None
                return redirect(url_for('forgotpassword', email=email))

        if request.method == 'POST': #if user inputs code and new password
            insertedcode = request.form.get('code')
            newpassword = request.form.get('password')
            password_hash = custom_hash(newpassword)

            if custom_hash(insertedcode) == session['code'] and email == session['email']: #compare codes (both hashed) and emails
                changepassword(email, password_hash) #update password
                session.clear() #clear session so code cant be used again
                return redirect(url_for('login'))
            
            return "incorrect code" #check for incorrect code
        
        return render_template('changepassword.html', email=email)

    #if no email is inputed
    if request.method == 'POST': #user inputs email
        email = request.form.get('email')
        return redirect(url_for('forgotpassword', email=email)) #page is reloaded with an email
    
    return render_template('forgotpassword.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)