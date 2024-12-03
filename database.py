#this file handles the database connection and queries

import sqlite3
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

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
        tagid = cursor.fetchone()

        cursor.execute('''
        INSERT INTO booktags (tagid, bookid)
        VALUES (?, ?)
        ''', (tagid[0], cursor.lastrowid))
        conn.commit()
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

def addtransaction(bookid, sellerid, buyerid):
    cursor.execute('''
    INSERT INTO transactions (bookid, sellerid, buyerid, time)
    VALUES (?, ?, ?, datetime('now'))
    ''', (bookid, sellerid, buyerid))
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