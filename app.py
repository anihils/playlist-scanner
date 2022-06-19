import base64
import os
import random
import requests
from urllib.parse import urlencode, urlparse
from flask import *


AUTH_URL = 'https://accounts.spotify.com/authorize?'
TOKEN_URL = 'https://accounts.spotify.com/api/token/'
BASE_URL = 'https://api.spotify.com/v1/'

CLIENT_ID = 'a6fe6798224848ab9c89445188c7e91b' # client id
CLIENT_SECRET = 'df4448d07ebf406b97fc172f97b946ca' # secret
REDIRECT_URI = 'http://localhost:5000/callback/' # redirect uri

def generateState():
    options = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    state = ''
    for i in range(16):
        index = random.randint(0, len(options) - 1)
        state += options[index]
    return state

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    state = generateState()
    scope = 'user-read-private playlist-read-private'
    params = {'response_type': 'code', 'client_id': CLIENT_ID, 'scope': scope, 'redirect_uri': REDIRECT_URI, 'state': state, 'show_dialog': False }
    return make_response(redirect(AUTH_URL + urlencode(params))) # TODO: cookie state

access_token = None
refresh_token = None
song_name = ''

@app.route('/callback/')
def callback():
    auth_code = request.args['code']
    params = {
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
      }

    auth_response = requests.post(TOKEN_URL, auth=(CLIENT_ID, CLIENT_SECRET), data=params).json()
    global access_token
    access_token = auth_response.get('access_token')
    global refresh_token
    refresh_token = auth_response.get('refresh_token')
    return render_template('test.html')

@app.route('/refresh')
def refresh():

    params = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    res = requests.post(TOKEN_URL, auth=(CLIENT_ID, CLIENT_SECRET), data=params, headers=headers)
    refresh_response = res.json()
    global access_token
    access_token = refresh_response.get('access_token')
    return

# Search all playlists
@app.route('/playlists')
def playlists():
    global song_name
    song_name = request.args['name'].lower()
    print(song_name)

    playlists_done = False
    url = BASE_URL + 'me/playlists?limit=50&offset=0'
    playlists = scan_items(url, 'playlists', None)

    data = []
    for id in playlists.keys():
        url = BASE_URL + 'playlists/' + id + '/tracks?limit=50&offset=0'
        results = scan_items(url, 'songs', playlists[id])
        for result in results.items():
            data.append(result)

    return render_template('result.html', result=song_name, data=data)

def scan_items(url, item_type, playlist):
    done = False
    playlist_info = {}

    redirect(url_for('refresh'))   
    while (done is False):
        headers = { 'Authorization': 'Bearer ' + access_token }
        content = requests.get(url, headers=headers).json()
        if item_type == 'playlists':
            for item in content['items']:
                playlist_info[item['id']] = item['name']
            url = content['next']
        else:
            for item in content['items']:
                if item['track'] is not None:
                    name = item['track']['name']
                    artist = item['track']['artists'][0]['name']
                    if(name.lower() == song_name):
                        playlist_info[artist] = playlist
                        print(artist + ': ' +  name + ' in ' + playlist)
            url = content['next']   

        if url is None:
            done = True
        else:
            redirect(url_for('refresh'))

    return playlist_info

if __name__ == "__main__":
    app.run(debug=True)