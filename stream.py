# -*- coding: utf-8 -*-

import json
import requests
import xbmcplugin,xbmcgui,xbmcaddon, xbmc
import sys
from utils import replaceWords, WORD_DIC
from hashlib import md5
from time import time

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
LOGIN_USER_AGENT = 'SznFrpcAnd2'
LOGIN_URL = 'https://login.szn.cz/api/v1/sessions'
BASE_URL = 'https://www.stream.cz/API'

addon = xbmcaddon.Addon('plugin.video.dmd-czech.stream')

class InvalidCredentials(Exception):
    pass

def api_password(url):
     return md5(('fb5f58a820353bd7095de526253c14fd'
            + url.split('/API')[1]
            + str(int(round(int(time()) / 3600.0 / 24.0))))
            .encode()).hexdigest()


def get_session(force_login=False):
    current = addon.getSetting('session')

    current_hash = md5(addon.getSetting('username')
        + addon.getSetting('password')).hexdigest()

    # this is to force relogin when credentials change
    if current and current.split(':')[0] == current_hash and not force_login:
        return current

    body = {
        'username': addon.getSetting('username'),
        'password': md5(addon.getSetting('password')).hexdigest(),
        'password_type': 'md5',
        'service': 'stream',
    }

    h = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json ',
        'User-Agent': LOGIN_USER_AGENT,
    }

    response = requests.post(LOGIN_URL,
            data=json.dumps(body),
            headers=h)

    data = json.loads(response.text)

    if data['status'] == 200:
        addon.setSetting('session', '%s:%s' % (current_hash, data['session']))
        return data['session']

    if data['status'] == 401:
        raise InvalidCredentials(data['message'])


def make_headers(url, use_login=False):
    headers = {
        'User-Agent': USER_AGENT,
        'Api-Password': api_password(url),
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json, */*',
    }

    if use_login:
        headers['Cookie'] = 'ds=' + get_session();

    return headers


def get_json(url):
    h = make_headers(url)
    response = requests.get(url, headers=h)
    text = replaceWords(response.text.encode('UTF-8'), WORD_DIC)

    return json.loads(text)


def authorized_request(url, method='get', data=None, retry=True):
    h = make_headers(url, True)
    res = requests.request(method, url, headers=h, data=data)
    response = json.loads(res.text)

    # if login failed (might expire), regenerate cookie and try again
    if res.status_code == 403:
        get_session(True)
        return authorized_request(url, method, data, False)

    return response


def query_favourites(ids):
    url = BASE_URL + '/shows/query_favourite'
    body = json.dumps({'shows': ids})

    response = authorized_request(url, 'post', body)
    shows = list(response['_embedded']['stream:favourite'])

    return [s['id'] for s in shows if s['is_favourite']]


def favourite(show_id, subscribe):
    url = '%s/show/%s/favourite' % (BASE_URL, show_id)
    method = 'PUT' if subscribe else 'DELETE'
    authorized_request(url, method)

# vim:set sw=4 ts=4 et:

