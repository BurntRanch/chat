from flask import Flask, request, Response, json
from time import time
import helper

app = Flask(__name__)

'''
main route because why not?
'''
@app.route('/')
def main():
    # status 418 ensures 2 things
    # 1. that the connection is stable & the server is responsive (if its 200 then the connection shouldn't be trusted because it could be compromised or unstable)
    # 2. funny
    return Response(status=418)

'''
get the latency, might be used later but right now it's useless

ARGUMENTS:
    json:
        time: send time, used to calculate latency.

RETURNS:
    json:
        lat: calculated recieve latency
        time: the time of recieving, could be used to calculate transmit latency

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/ping')
def ping():
    t = time()
    try:
        return Response(json.dumps({"lat": t-float(request.form['time']), "time": t}))
    except ValueError:
        return Response(helper.generateError(7), status=helper.getErrorHttpCode(7))

'''
main login endpoint

ARGUMENTS:
    json:
        user: username
        pass: password

RETURNS:
    json:
        token: returns the token for the account

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/login')
def login():
    if helper.isLoginInfoProvided(request.form):
        return Response(helper.generateError(1), status=helper.getErrorHttpCode(1))
    code = helper.authenticate(request.form['user'], request.form['pass'])
    if isinstance(code, str):
        return Response(json.dumps({'token': code}), status=200)
    else:
        return Response(helper.generateError(code), status=helper.getErrorHttpCode(code))

'''
main signup endpoint

ARGUMENTS:
    json:
        user: username
        pass: password

RETURNS:
    json:
        msg: message for the user

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/signup', methods=["POST"])
def signup():
    if helper.isLoginInfoProvided(request.form):
        return Response(helper.generateError(1), status=helper.getErrorHttpCode(1))
    code = helper.writeUserInfo(request.form['user'], request.form['pass'])
    if code == 0:
        return Response(json.dumps({'msg': "Successfully signed up!"}), status=200)
    else:
        return Response(helper.generateError(code), status=helper.getErrorHttpCode(code))

'''
main information endpoint

ARGUMENTS:
    json:
        token: your auth token
        uuid: optional, the uuid to lookup

RETURNS:
    json:
        name: the name of the user

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/get-info')
def getinfo():
    if not helper.isAuthenticated(request.form.get('token', 'err')):
        return Response(helper.generateError(8), status=helper.getErrorHttpCode(8))
    info = helper.getinfo(helper.getUUID(request.form['token']) if 'uuid' not in request.form else request.form['uuid'])
    return Response(json.dumps({"name": info}), status=200)

'''
main logout endpoint

ARGUMENTS:
    json:
        token: your auth token

RETURNS:
    json:
        msg: human readable message

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/logout', methods=["POST"])
def logout():
    code = helper.logout(request.form.get('token', 'err'))
    if code == 0:
        return Response(json.dumps({'msg': "Successfully logged out!"}), status=200)
    else:
        return Response(helper.generateError(code), status=helper.getErrorHttpCode(code))

'''
main message recieving endpoint

ARGUMENTS:
    json:
        token: your auth token
    args:
        page: optional, every page is 10 messages, this value can be used to scroll across pages
        after: optional, get every message after the specified time in epoch milliseconds

RETURNS:
    json:
        messages: a list of every message with the above filters applied, this value is reversed and is formatted like this:
                [[messageID, content, author UUID, time]]

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
# TODO: reverse the value before sending it for ease?
@app.route('/get-messages')
def getmessages():
    if not helper.isAuthenticated(request.form.get('token', 'err')):
        return Response(helper.generateError(8), status=helper.getErrorHttpCode(8))
    try:
        messages = helper.getMessages(int(request.args.get('page', 0)), float(request.args.get('after', 0)))
        return Response(json.dumps({'messages': messages}), status=200)
    except ValueError:
        return Response(helper.generateError(7), status=helper.getErrorHttpCode(7))

'''
main message sending endpoint

ARGUMENTS:
    json:
        token: your auth token
        content: message content

RETURNS:
    json:
        msg: human readable message
        messageID: message ID, can be used with other endpoints to interact with messages

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/send-message', methods=["POST"])
def sendmessage():
    if not helper.isAuthenticated(request.form.get('token', 'err')):
        return Response(helper.generateError(8), status=helper.getErrorHttpCode(8))
    if not 'content' in request.form:
        return Response(helper.generateError(9), status=helper.getErrorHttpCode(9))
    try:
        messageID = helper.sendMessage(request.form['content'], request.form['token'])
        return Response(json.dumps({'msg': 'Message sent successfully!', 'messageID': messageID}), status=200)
    except ValueError:
        return Response(helper.generateError(7), status=helper.getErrorHttpCode(7))

'''
main message deletion endpoint

ARGUMENTS:
    json:
        token: your auth token
        messageID: the message ID to delete, it has to be owned by the user.

RETURNS:
    json:
        msg: human readable message

This function can error, in which it will return this instead:
{"code": (error code), "msg": (human readable message)}
'''
@app.route('/delete-message', methods=["POST"])
def deletemessage():
    if not helper.isAuthenticated(request.form.get('token', 'err')):
        return Response(helper.generateError(8), status=helper.getErrorHttpCode(8))
    if not 'messageID' in request.form:
        return Response(helper.generateError(9), status=helper.getErrorHttpCode(9))
    try:
        code = helper.deleteMessage(request.form['messageID'], request.form['token'])
        if code == 0:
            return Response(json.dumps({'msg': 'Message deleted successfully!'}), status=200)
        else:
            return Response(helper.generateError(code), status=helper.getErrorHttpCode(code))
    except ValueError:
        return Response(helper.generateError(7), status=helper.getErrorHttpCode(7))

'''
rate limiting middleware

this function will setup IP sessions and rate limit tokens/IPs

for signed-in accounts the rate limit is max 20 requests per 5 seconds
for anonymous "IP sessions" the rate limit is max 10 requests per 10 seconds
'''
def before_request():
    # authenticated by token?
    is_auth = helper.isAuthenticated(request.form.get('token', 'err'))
    if is_auth and not request.url_rule.rule ==  '/logout':
        # get their rate limit and the last time the rate limit was incremented
        rateLimit = helper.getSessionRateLimit(request.form.get('token', 'err'))
        isDecremented = False
        # more than 5 seconds? decrement it.
        if time() >= rateLimit[1] and rateLimit[0] > 0:
            helper.resetSessionRateLimit(request.form['token'])
            rateLimit = (rateLimit[0]-1, rateLimit[1])
            isDecremented = True
        # still more than 20 requests? return error.
        if rateLimit[0] >= 20:
            return Response(helper.generateError(11), status=helper.getErrorHttpCode(11))
        if not isDecremented:
            helper.incrementSessionRateLimit(request.form['token'])
            print(f'incremented rate limit for {request.form["token"]} to {rateLimit[0]+1}')
    elif helper.isIPSession(request.remote_addr) and not is_auth:
        # get their rate limit and the last time the rate limit was incremented
        rateLimit = helper.getSessionRateLimit(request.remote_addr)
        isDecremented = False
        if time() >= rateLimit[1] and rateLimit[0] > 0:
            helper.resetSessionRateLimit(request.remote_addr)
            print(f"decremented rate limit for {request.remote_addr} to {rateLimit[0] - 1}")
            rateLimit = (rateLimit[0]-1, rateLimit[1])
            isDecremented = True
        # still more than 10 requests? return error.
        if rateLimit[0] >= 10:
            return Response(helper.generateError(11), status=helper.getErrorHttpCode(11))
        if not isDecremented:
            helper.incrementSessionRateLimit(request.remote_addr)
            print(f'incremented rate limit for {request.remote_addr} to {rateLimit[0]+1}')
    elif not is_auth:
        helper.createIPSession(request.remote_addr)
    return None

app.before_request(before_request)

app.run('0.0.0.0')