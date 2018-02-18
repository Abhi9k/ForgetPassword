from flask import Flask,render_template,request,redirect
import requests
import json
import base64
from flask import jsonify
import os
from datetime import datetime
app = Flask(__name__)

#domain = "env-66916.customer.cloud.microstrategy.com:2443"
domain = "env-84684.customer.cloud.microstrategy.com:2443"
clientId = "13"
orgId = "2"
session = requests.session()


def add_new_ssid_password(ssid, password):
    with open("db/passwords/" + ssid, 'w') as f:
        f.write(password+"\n")

def append_ssid_user_list(ssid, user_list):
    with open("db/users/" + ssid, 'w') as f:
        for user in user_list:
            f.write(user + "\n")

def get_ssid_user_mapping():
    ssids = os.listdir("db/users")
    resp = {}
    for ssid in ssids:
        with open("db/users/" + ssid, 'r') as f:
            lines = f.readlines()
            lines = [x.strip() for x in lines]
            resp[ssid] = lines
    return resp

def get_ssid_password(ssid):
    password = ''
    with open("db/passwords/" + ssid, 'r') as f:
        password = f.readlines()[0].strip()
    return password
    
def get_ssid_password_mapping():
    resp = {}
    ssids = os.listdir("db/passwords")
    for ssid in ssids:
        password = get_ssid_password(ssid)
        resp[ssid] = password
    return resp

def add_new_ssid(ssid, password, user_list):
    if password:
        add_new_ssid_password(ssid, password)
    if user_list:
        append_ssid_user_list(ssid, user_list)
    return {"response": "ok"}

def get_all_dataset():
    response = []
    ssid_user_mapping = get_ssid_user_mapping()
    ssid_password_mapping = get_ssid_password_mapping()
    for ssid in ssid_user_mapping.keys():
        users = ssid_user_mapping[ssid]
        password = ssid_password_mapping[ssid]
        response.append({"ssid": ssid, "password": password, "users": users})
    print response
    return response

@app.route('/newuser/<ssid>/<password>/<user>')
def add_new_ssid_route(ssid, password, user):
    user = str(user)
    add_new_ssid(ssid, password, user.split(','))
    return redirect('/')    

@app.route('/addsession/<user_email>')
def add_new_session(user_email):
    print user_email
    with open('db/sessions/' + user_email, 'w') as f:
        timestamp = datetime.now().strftime("%s")
        f.write(timestamp + '\n')

@app.route('/')
def welcome():
    data = get_all_dataset()
    print data
    return render_template('home.html', items=data)


@app.route('/addssid')
def addssid():
    return render_template('addssid.html')

@app.route('/authenticated/<user_email>')
def check_authentication(user_email):
    resp = {"session": "not scanned"}
    try:
        f = open('db/sessions/' + user_email, 'r')
        timestamp = f.readlines()[0].strip()
        curr_time = datetime.now().strftime("%s")
        if(int(curr_time)-int(timestamp) <=120):
            return jsonify({"session": "ok"})
        else:
            return jsonify(resp)
    except:
        return jsonify(resp)

@app.route('/user/<user_email>')
def fetch_user_wifis(user_email):
    print user_email
    ssid_user_mapping = get_ssid_user_mapping()
    resp = []
    ssid_password_mapping = get_ssid_password_mapping()
    for ssid in ssid_password_mapping.keys():
        password = ssid_password_mapping[ssid]
        users = ssid_user_mapping[ssid]
        if user_email in users:
            resp.append({"ssid": ssid, "password": password})
    return jsonify(resp)

@app.route('/password/<ssid>')
def get_password(ssid):
    print ssid
    password = get_ssid_password(ssid)
    return jsonify({"ssid": ssid, "password": password})



@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/qr')
def display_qr():
    return render_template('qr.html')


# API to shutdown the server
@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

# Generate QR code
@app.route('/genQRcode', methods=['POST'])
def genQRcode():
    ssoCreateAPI = "https://" + domain + "/sso/create_registration_session"
    payload = {'client_id': clientId,
               'return_image': 'true',
               'session_data': '{"descirption":"RESTSample"}'
    }
    response = session.post(ssoCreateAPI, payload)
    # print response.content
    return json.dumps(response.json())


# Check if QR code has been scanned
# Return token if successfully scan the QR code
@app.route('/ssowait')
def ssoWait():
    ssoWaitAPI = "https://" + domain + "/sso/wait" + "?session_type=nonblock" + "&client_id=" + clientId
    response = session.get(ssoWaitAPI)
    respDict = response.json()
    if 'access_token' in respDict:
        accessToken = respDict['access_token']
        session.cookies.set("token", accessToken)
        return getBadgeInfo()
    else:
        return json.dumps(respDict)


# Get info of the badge that scans the QR code
def getBadgeInfo():
    accessToken = session.cookies.get("token")
    badgeOrgUrl = "https://" + domain + "/badge/org/" + orgId + "?uid_only=false&access_token=" + accessToken
    badgeRes = session.get(badgeOrgUrl)
    session.cookies.set("token", accessToken)
    badgeId = badgeRes.json()[0]['id']
    session.cookies.set("badgeId", str(badgeId))
    return json.dumps(badgeRes.json()[0])

# Retrieve badge image
@app.route('/badgeImage')
def getBadgeImage():
    accessToken = session.cookies.get("token")
    badgeId = session.cookies.get("badgeId")
    badgeImageUrl = "https://" + domain + "/user/get_public_image/badge/" + badgeId + "?access_token=" + accessToken
    badgeImageResponse = session.get(badgeImageUrl)
    session.cookies.clear()
    return base64.encodestring(badgeImageResponse.content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", ssl_context=('nonsaml-client-cert.crt', 'domain.com.key'))
