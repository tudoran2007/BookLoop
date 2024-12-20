#this file handles the database connection and queries

from misc import *
import sqlite3
db = sqlite3.connect('database.db', check_same_thread=False)

cursor = db.cursor()

#database settings to prevent database locking
db.execute('PRAGMA journal_mode=WAL;')
db.execute('PRAGMA busy_timeout = 1000;')

#create all the tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    password VARCHAR
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    title VARCHAR,
    author VARCHAR,
    description VARCHAR,
    currentowner INTEGER,
    FOREIGN KEY (currentowner) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    bookid INTEGER,
    sellerid INTEGER,
    buyerid INTEGER,
    time DATETIME,
    FOREIGN KEY (bookid) REFERENCES books (id),
    FOREIGN KEY (sellerid) REFERENCES users (id),
    FOREIGN KEY (buyerid) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    tagname VARCHAR
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS booktags (
    tagid INTEGER,
    bookid INTEGER,
    PRIMARY KEY (tagid, bookid),
    FOREIGN KEY (tagid) REFERENCES tags (id),
    FOREIGN KEY (bookid) REFERENCES books (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS chats (
    chatid INTEGER,
    userid INTEGER,
    PRIMARY KEY (chatid, userid),
    FOREIGN KEY (userid) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    sender VARCHAR,
    chat INTEGER,
    time DATETIME,
    message VARCHAR,
    FOREIGN KEY (sender) REFERENCES users (id),
    FOREIGN KEY (chat) REFERENCES chats (chatid)
)
''')

def adduser(username, email, password): #function to create a new user
    cursor.execute('''
    INSERT INTO users (username, email, password)
    VALUES (?, ?, ?)
    ''', (username, email, password))
    db.commit()

def checklogin(username, password): #checks if the login credentials are correct and returns bool
    cursor.execute('''
    SELECT * FROM users
    WHERE username = ? AND password = ?
    ''', (username, password))
    return (cursor.fetchone() is not None)

def changepassword(username, password): #changes the password of a user
    cursor.execute('''
    UPDATE users
    SET password = ?
    WHERE username = ?
    ''', (custom_hash(password), username))
    db.commit()

def addbook(title, author, description, currentowner, tags): #adds a book to the database
    cursor.execute('''
    INSERT INTO books (title, author, description, currentowner)
    VALUES (?, ?, ?, ?)
    ''', (title, author, description, currentowner)) #add title, author, description and current owner

    for i in tags: #adds tags one by one to booktags table
        cursor.execute('''
        SELECT id FROM tags
        WHERE tagname = ?
        ''', (i,))

        tagid = cursor.fetchone()[0]
        bookid = cursor.execute('''
        SELECT id FROM books
        WHERE title = ? AND author = ? AND description = ? AND currentowner = ?
        ORDER BY id DESC''', (title, author, description, currentowner)).fetchone()[0]

        cursor.execute('''
        INSERT INTO booktags (tagid, bookid)
        VALUES (?, ?)
        ''', (tagid, bookid))
    
    db.commit()

def changepassword(email, password): #updates password
    cursor.execute('''
    UPDATE users
    SET password = ?
    WHERE email = ?
    ''', (password, email))
    db.commit()

def addtag(tagname): #adds a tag to the database
    cursor.execute('''
    INSERT INTO tags (tagname)
    VALUES (?)
    ''', (tagname,))
    db.commit()

def editbook(bookid, title, author, description, tags): #edit a book
    cursor.execute('''
    UPDATE books
    SET title = ?, author = ?, description = ?
    WHERE id = ?
    ''', (title, author, description, bookid)) #change name, author and description

    cursor.execute('''
    DELETE FROM booktags
    WHERE bookid = ?
    ''', (bookid,)) #remove old tags
    db.commit()

    for i in tags: #add new tags
        cursor.execute('''
        SELECT id FROM tags
        WHERE tagname = ?
        ''', (i,))
        tagid = cursor.fetchone()

        cursor.execute('''
        INSERT INTO booktags (tagid, bookid)
        VALUES (?, ?)
        ''', (tagid[0], bookid))
        db.commit()

def deletebook(bookid): #remove a book completely
    cursor.execute('''
    DELETE FROM books
    WHERE id = ?
    ''', (bookid,)) #remove book from books table

    cursor.execute('''
    DELETE FROM booktags
    WHERE bookid = ?
    ''', (bookid,)) #remove tag data

    cursor.execute('''
    DELETE FROM transactions
    WHERE bookid = ?
    ''', (bookid,)) #remove transaction data
    
    db.commit()

def transferbook(bookid, sellerid, buyerid): #transfer a book from one user to another
    cursor.execute('''
    UPDATE books SET currentowner = ?
    WHERE id = ?''', (buyerid, bookid)) #set new owner
    db.commit()

    cursor.execute('''
    INSERT INTO transactions
    (bookid, sellerid, buyerid, time)
    VALUES (?, ?, ?, datetime('now'))''', (bookid, sellerid, buyerid)) #log transaction
    db.commit()

def createchat(user1id, user2id): #create a chat between two users
    try: #get the latest chat id
        latestchat = cursor.execute("SELECT chatid FROM chats ORDER BY chatid DESC").fetchone()[0]
    except:
        latestchat = 0

    cursor.execute('''
    INSERT INTO chats (chatid, userid)
    VALUES (?, ?)
    ''', (latestchat+1, user1id)) #link chat to user 1
    db.commit()
    
    cursor.execute('''
    INSERT INTO chats (chatid, userid)
    VALUES (?, ?)
    ''', (latestchat+1, user2id)) #link chat to user 2
    db.commit()

def chatbetween(user1id, user2id): #return the chat id between two users
    try:
        id = cursor.execute('''
        SELECT chatid FROM chats
        WHERE userid = ? AND chatid IN (SELECT chatid FROM chats WHERE userid = ?)
        ''', (user1id, user2id)).fetchone()[0]
    except:
        id = None
    return id

def sendmessage(sender, chat, message): #send a message to a chat
    cursor.execute('''
    INSERT INTO messages (sender, chat, time, message)
    VALUES (?, ?, datetime('now'), ?)
    ''', (sender, chat, message))
    db.commit()

def getuserid(username): #return the id of the user with the given username
    cursor.execute('''
    SELECT id FROM users
    WHERE username = ?
    ''', (username,))

    return cursor.fetchone()[0]

if cursor.execute("SELECT * FROM tags").fetchone() is None: #these are some example tags that are added to the database if there are no tags
    tags = [
    'Fiction',
    'Non-Fiction',
    'Mystery',
    'Fantasy',
    'Science Fiction',
    'Biography',
    'History',
    'Romance',
    'Thriller',
    'Self-Help',
    'Health',
    'Travel',
    'Education',
    'Religion',
    'Science',
    'Poetry',
    'Drama',
    'Adventure',
    'Horror',
    'Comics'
    ]
    for i in tags:
        addtag(i)