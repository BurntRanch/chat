from getpass import getpass
import requests
import time
import asyncio
from threading import Thread

token = None

while True:
    username = input("Username > ")
    password = getpass("Password > ")

    r = requests.get("http://127.0.0.1:5000/login", data={"user": username, "pass": password})

    if r.status_code == 200:
        token = r.json()['token']
    else:
        print(r.json()['msg'])
        continue
    break

print("Welcome to the chat!")

r = requests.get("http://127.0.0.1:5000/get-messages", data={"token": token}).json()
latest_message_time = 0
if 'messages' in r:
    messages = r['messages']
    if len(messages) > 0:
        latest_message_time = messages[0][3]
        for message in messages[::-1]:
            r = requests.get("http://127.0.0.1:5000/get-info", data={"token": token, "uuid": message[2]}).json()
            print(f'{r["name"]}: {message[1]}')
else:
    print(r['msg'])

def update():
    global latest_message_time
    try:
        LINE_UP = '\033[1A'
        LINE_CLEAR = '\x1b[2K'
        t = 1
        while not time.sleep(t):
            r = requests.get(f"http://127.0.0.1:5000/get-messages?after={latest_message_time}", data={"token": token}).json()
            if 'messages' in r:
                messages = r['messages']
                if len(messages) > 0:
                    latest_message_time = r['messages'][0][3]
                    for message in messages[::-1]:
                        r = requests.get("http://127.0.0.1:5000/get-info", data={"token": token, "uuid": message[2]}).json()
                        if 'name' in r:
                            print(LINE_UP, end=LINE_CLEAR)
                            print(f'{r["name"]}: {message[1]}')
                            print(">> ")
                else:
                    t = 5
    except Exception as e:
        print("Exception!", e.args)

def main():
    t = Thread(target=update, daemon=True)
    t.start()
    sendMessages()

def sendMessages():
    global latest_message_time
    LINE_UP = '\033[1A'
    LINE_CLEAR = '\x1b[2K'
    latest_message_ID = ""
    while True:
        msg = input("[For CMDs, type .cmds] >> ")
        print(LINE_UP, end=LINE_CLEAR)
        if not msg.startswith('.'):
            r = requests.post('http://127.0.0.1:5000/send-message', data={"token": token, "content": msg})
            if r.status_code == 200:
                latest_message_time = time.time()
                latest_message_ID = r.json()['messageID']
                print(f'{username}: {msg}')
            else:
                print('Failed to send message:', r.json()['msg'])
        else:
            if msg == '.help':
                print('Commands:')
                print('.delete: Deletes your latest message.')
            if msg == '.delete':
                r = requests.post('http://127.0.0.1:5000/delete-message', data={"token": token, "messageID": latest_message_ID})
                if r.status_code != 200:
                    print("Could not delete message!", r.json()['msg'])
                else:
                    print("Deleted message successfully!")

try:
    asyncio.run(main())
finally:
    print("Logging out!")
    requests.post("http://127.0.0.1:5000/logout", data={"token": token})
