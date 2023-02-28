'''
================== helper.py ==================
    this file is meant to help the server
    serve it's content safely and easily.

    You should only consider looking at this
 if you're looking for security vulnerabilities.
'''

import json
import sqlite3
from time import time
from bcrypt import hashpw, checkpw, gensalt
from hashlib import md5, sha256
from secrets import token_hex

AUTHENTICATED_RATELIMIT_TIMER = 2
RATELIMIT_TIMER = 10

connection = sqlite3.connect("main.db")
try:
    connection.execute("CREATE TABLE IF NOT EXISTS users (username STRING, uuid STRING PRIMARY KEY UNIQUE, password STRING)")
    connection.execute("CREATE TABLE IF NOT EXISTS sessions (uuid STRING, token STRING PRIMARY KEY UNIQUE, limitTimer INTEGER, lastTimerTime FLOAT, expires FLOAT, type INTEGER DEFAULT 1)")
    connection.execute("CREATE TABLE IF NOT EXISTS messages (messageID STRING PRIMARY KEY UNIQUE, content STRING, authorUUID STRING, time FLOAT)")
finally:
    connection.close()

errorLookup = {
    1: ["You must specify the USERNAME and PASSWORD fields in the data", 400],
    2: ["Invalid login information!", 400],
    3: ["Internal Server Error!", 500],
    4: ["Invalid username/password!", 400],
    5: ["User already exists!", 400],
    6: ["No authentication provided!", 401],
    7: ["You must provide a valid argument!", 400],
    8: ["Not authorized!", 403],
    9: ["Missing Argument!", 400],
    10: ["Content not found!", 404],
    11: ["Too many requests!", 429]
}

isLoginInfoProvided = lambda form: not 'user' in form or not 'pass' in form

def isLoginInfoValid(username : str, password : str):
    for c in (username + password):
        if not 126 >= ord(c) >= 32:
            return False
    return True

generateError = lambda code: json.dumps({'code': code, 'msg': errorLookup.get(code, None)[0]})
getErrorHttpCode = lambda code: errorLookup.get(code, [None, 500])[1]

def writeUserInfo(username : str, password : str):
    if not isLoginInfoValid(username, password):
        return 2
    # allows us to see the scope of an error if we seperate backend and frontend functions
    return _writeUserInfo(username, password)

def _writeUserInfo(username : str, password : str):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT EXISTS(SELECT 1 FROM users WHERE uuid = ?)", (md5(username.encode()).hexdigest(),))
        if cursor.fetchone()[0] == 0:
            connection.execute("INSERT INTO users VALUES (?, ?, ?)", (username, md5(username.encode()).hexdigest(), hashpw(password.encode(), gensalt())))
        else:
            return 5
    except Exception as e:
        print(e.args)
        return 3
    finally:
        commitAndClose(connection)
    return 0

def authenticate(username : str, password : str):
    uuid = md5(username.encode()).hexdigest()
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT EXISTS(SELECT 1 FROM users WHERE uuid = ?)", (uuid,))
        if cursor.fetchone()[0] == 1:
            cursor = connection.execute("SELECT password FROM users WHERE uuid = ?", (uuid,))
            if checkpw(password.encode(), cursor.fetchone()[0]):
                token = token_hex()
                connection.execute("INSERT INTO sessions VALUES (?, ?, 0, ?, ?, 1)", (uuid, sha256(token.encode()).hexdigest(), time(), time()+300))
                return token
            return 4
        else:
            return 4
    except Exception as e:
        print(e.args)
        return 3
    finally:
        commitAndClose(connection)

def isAuthenticated(token : str):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT EXISTS(SELECT 1 FROM sessions WHERE token = ? AND expires > ? AND type = 1)", (sha256(token.encode()).hexdigest(), time()))
        return cursor.fetchone()[0] == 1
    finally:
        commitAndClose(connection)

def getUUID(token : str):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT uuid FROM sessions WHERE token = ?", (sha256(token.encode()).hexdigest(),))
        return cursor.fetchone()[0]
    finally:
        commitAndClose(connection)

def getinfo(uuid : str):
    connection = sqlite3.connect("main.db")
    try:
        print(uuid)
        cursor = connection.execute("SELECT username FROM users WHERE uuid = ?", (uuid,))
        return cursor.fetchone()[0]
    finally:
        commitAndClose(connection)

def logout(token : str):
    connection = sqlite3.connect("main.db")
    try:
        if isAuthenticated(token):
            connection.execute("DELETE FROM sessions WHERE token = ?", (sha256(token.encode()).hexdigest(),))
            return 0
        else:
            return 6
    finally:
        commitAndClose(connection)

def incrementSessionRateLimit(token : str):
    connection = sqlite3.connect("main.db")
    is_real = isAuthenticated(token)
    try:
        if is_real or isIPSession(token):
            connection.execute("UPDATE sessions SET limitTimer = limitTimer + 1, lastTimerTime = ? WHERE token = ?", (time()+(RATELIMIT_TIMER if not is_real else AUTHENTICATED_RATELIMIT_TIMER), sha256(token.encode()).hexdigest(),))
            return 0
        else:
            return 6
    finally:
        commitAndClose(connection)

def decrementSessionRateLimit(token : str):
    connection = sqlite3.connect("main.db")
    is_real = isAuthenticated(token)
    try:
        if is_real or isIPSession(token):
            connection.execute("UPDATE sessions SET limitTimer = limitTimer - 1, lastTimerTime = ? WHERE token = ?", (time()+(RATELIMIT_TIMER if not is_real else AUTHENTICATED_RATELIMIT_TIMER), sha256(token.encode()).hexdigest(),))
            return 0
        else:
            return 6
    finally:
        commitAndClose(connection)

def resetSessionRateLimit(token : str):
    connection = sqlite3.connect("main.db")
    is_real = isAuthenticated(token)
    try:
        if isAuthenticated(token) or isIPSession(token):
            connection.execute("UPDATE sessions SET limitTimer = 0, lastTimerTime = ? WHERE token = ?", (time()+(RATELIMIT_TIMER if not is_real else AUTHENTICATED_RATELIMIT_TIMER), sha256(token.encode()).hexdigest(),))
            return 0
        else:
            return 6
    finally:
        commitAndClose(connection)

def createIPSession(ip : str):
    connection = sqlite3.connect("main.db")
    try:
        connection.execute("INSERT INTO sessions VALUES (?, ?, 0, ?, ?, 0)", ("_", sha256(ip.encode()).hexdigest(), time(), -1))
    except Exception as e:
        print(e.args)
        return 3
    finally:
        commitAndClose(connection)

def isIPSession(token : str):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT EXISTS(SELECT 1 FROM sessions WHERE token = ? AND type = 0)", (sha256(token.encode()).hexdigest(),))
        return cursor.fetchone()[0] == 1
    finally:
        commitAndClose(connection)

def getSessionRateLimit(token : str):
    connection = sqlite3.connect("main.db")
    try:
        if isAuthenticated(token) or isIPSession(token):
            cursor = connection.execute("SELECT limitTimer, lastTimerTime FROM sessions WHERE token = ?", (sha256(token.encode()).hexdigest(),))
            return cursor.fetchone()
        return 0
    finally:
        commitAndClose(connection)

def getMessages(page : int, after : float):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT * FROM messages WHERE time > ? ORDER BY time DESC LIMIT 10 OFFSET ?", (after, page*10))
        return cursor.fetchall()
    finally:
        commitAndClose(connection)

def sendMessage(content : str, token : str):
    connection = sqlite3.connect("main.db")
    try:
        messageID = token_hex()
        connection.execute("INSERT INTO messages VALUES (?, ?, ?, ?)", (messageID, content, getUUID(token), time()))
        return messageID
    finally:
        commitAndClose(connection)

def deleteMessage(messageID : str, token : str):
    connection = sqlite3.connect("main.db")
    try:
        cursor = connection.execute("SELECT authorUUID FROM messages WHERE messageID = ?", (messageID,))
        uuid = cursor.fetchone()
        if uuid is None:
            return 10
        uuid ,= uuid
        if getUUID(token) == uuid:
            connection.execute("DELETE FROM messages WHERE messageID = ?", (messageID,))
            return 0
        return 8
    finally:
        commitAndClose(connection)

def commitAndClose(connection : sqlite3.Connection):
    connection.commit()
    connection.close()
