from getpass import getpass
import requests
import time
import asyncio
from threading import Thread
from urllib3.util.url import parse_url
from urllib.parse import quote

token = None
IP = parse_url(input('Insert server ip: '))
while True:
    try:
        IP = IP.host + (':' + str(IP.port) if IP.port is not None else '')
        assert requests.get(f'https://{IP}/').status_code == 418
    except Exception as e:
        print('That server is either nonexistent, running an incompatible server, or irresponsive.')
    else:
        break
    IP = parse_url(input('Insert server ip: '))
    continue

action = input('What would you like to do? [L = Log-in, S = Sign-up] ').lower()
while True:
    username = input("Username > ")
    password = getpass("Password > ")

    if action == 's':
        r = requests.post(f"https://{IP}/signup", data={"user": username, "pass": password})
    else:
        r = requests.get(f"https://{IP}/login", data={"user": username, "pass": password})

    if r.status_code == 200:
        if action == 's':
            r = requests.get(f"https://{IP}/login", data={"user": username, "pass": password})
        token = r.json()['token']
    else:
        print(r.json()['msg'])
        continue
    break

print("Welcome to the chat!")

r = requests.get(f"https://{IP}/get-messages", data={"token": token}).json()
latest_message_time = 0
if 'messages' in r:
    messages = r['messages']
    if len(messages) > 0:
        latest_message_time = messages[0][3]
        for message in messages:
            r = requests.get(f"https://{IP}/get-info", data={"token": token, "uuid": message[2]}).json()
            print(f'{r["name"]}: {message[1]}')
else:
    print(r['msg'])

def update():
    global latest_message_time
    try:
        LINE_CLEAR = '\x1b[2K'
        t = 1
        while not time.sleep(t):
            print(latest_message_time)
            r = requests.get(f"https://{IP}/get-messages?after={quote(str(latest_message_time))}", data={"token": token}).json()
            if 'messages' in r:
                messages = r['messages']
                if len(messages) > 0:
                    latest_message_time = r['messages'][0][3]
                    for message in messages:
                        r = requests.get(f"https://{IP}/get-info", data={"token": token, "uuid": message[2]}).json()
                        if 'name' in r:
                            print(LINE_CLEAR, end='\r')
                            print(f'{r["name"]}: {message[1]}')
                            print("[For CMDs, type .cmds] >> ", end='', flush=True)
                else:
                    # save bandwidth when there is nothing being sent.
                    t = 2
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
    while True:
        msg = input("[For CMDs, type .cmds] >> ")
        print(LINE_UP, end=LINE_CLEAR)
        if not msg.startswith('.'):
            r = requests.post(f'https://{IP}/send-message', data={"token": token, "content": msg})
            if r.status_code == 200:
                latest_message_time = time.time()
                print(f'{username}: {msg}')
            else:
                print('Failed to send message:', r.json()['msg'])
        else:
            if msg == '.help':
                print('Commands:')
                print('.delete: Deletes your latest message.')
                print()
            if msg == '.delete':
                r = requests.post(f'https://{IP}/delete-message', data={"token": token})
                if r.status_code != 200:
                    print("Could not delete message!", r.json()['msg'])
                else:
                    print("Deleted message successfully!")

try:
    asyncio.run(main())
finally:
    print("Logging out!")
    requests.post(f"https://{IP}/logout", data={"token": token})
