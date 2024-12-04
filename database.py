#this file handles the database connection and queries

import sqlite3
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
conn.execute('PRAGMA journal_mode=WAL;')
conn.execute('PRAGMA busy_timeout = 1000;')

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

def adduser(username, email, password):
    cursor.execute('''
    INSERT INTO users (username, email, password)
    VALUES (?, ?, ?)
    ''', (username, email, password))
    conn.commit()

def checklogin(username, password):
    cursor.execute('''
    SELECT * FROM users
    WHERE username = ? AND password = ?
    ''', (username, password))
    return (cursor.fetchone() is not None)

def changepassword(username, password):
    cursor.execute('''
    UPDATE users
    SET password = ?
    WHERE username = ?
    ''', (password, username))
    conn.commit()

def addbook(title, author, description, currentowner, tags):
    cursor.execute('''
    INSERT INTO books (title, author, description, currentowner)
    VALUES (?, ?, ?, ?)
    ''', (title, author, description, currentowner))

    for i in tags:
        cursor.execute('''
        SELECT id FROM tags
        WHERE tagname = ?
        ''', (i,))

        tagid = cursor.fetchone()[0]
        bookid = cursor.execute("SELECT id FROM books WHERE title = ? AND author = ? AND description = ? AND currentowner = ? ORDER BY id DESC", (title, author, description, currentowner)).fetchone()[0]

        cursor.execute('''
        INSERT INTO booktags (tagid, bookid)
        VALUES (?, ?)
        ''', (tagid, bookid))
    
    conn.commit()

def addtag(tagname):
    cursor.execute('''
    INSERT INTO tags (tagname)
    VALUES (?)
    ''', (tagname,))
    conn.commit()

def editbook(bookid, title, author, description, currentowner, tags):
    cursor.execute('''
    UPDATE books
    SET title = ?, author = ?, description = ?, currentowner = ?
    WHERE id = ?
    ''', (title, author, description, currentowner, bookid))

    cursor.execute('''
    DELETE FROM booktags
    WHERE bookid = ?
    ''', (bookid,))
    conn.commit()

    for i in tags:
        cursor.execute('''
        SELECT id FROM tags
        WHERE tagname = ?
        ''', (i,))
        tagid = cursor.fetchone()

        cursor.execute('''
        INSERT INTO booktags (tagid, bookid)
        VALUES (?, ?)
        ''', (tagid[0], bookid))
        conn.commit()
    conn.commit()

def deletebook(bookid):
    cursor.execute('''
    DELETE FROM books
    WHERE id = ?
    ''', (bookid,))
    conn.commit()

def transferbook(bookid, sellerid, buyerid):
    cursor.execute('''
    UPDATE books SET currentowner = ?
    WHERE id = ?''', (buyerid, bookid))
    conn.commit()

    cursor.execute('''
    INSERT INTO transactions
    (bookid, sellerid, buyerid, time)
    VALUES (?, ?, ?, datetime('now'))''', (bookid, sellerid, buyerid))
    conn.commit()

def createchat(user1id, user2id):
    try:
        latestchat = cursor.execute("SELECT chatid FROM chats ORDER BY chatid DESC").fetchone()[0]
    except:
        latestchat = 0

    cursor.execute('''
    INSERT INTO chats (chatid, userid)
    VALUES (?, ?)
    ''', (latestchat+1, user1id))
    conn.commit()
    
    cursor.execute('''
    INSERT INTO chats (chatid, userid)
    VALUES (?, ?)
    ''', (latestchat+1, user2id))
    conn.commit()

def chatbetween(user1id, user2id):
    try:
        id = cursor.execute('''
        SELECT chatid FROM chats
        WHERE userid = ? AND chatid IN (SELECT chatid FROM chats WHERE userid = ?)
        ''', (user1id, user2id)).fetchone()[0]
    except:
        id = None
    return id

def sendmessage(sender, chat, message):
    cursor.execute('''
    INSERT INTO messages (sender, chat, time, message)
    VALUES (?, ?, datetime('now'), ?)
    ''', (sender, chat, message))
    conn.commit()

if cursor.execute("SELECT * FROM tags").fetchone() is None:
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