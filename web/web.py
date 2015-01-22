#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import math
import codecs
import random
import requests
import configparser

from flask import Flask
from flask import jsonify
from flask import request
from flask import session
from flask import redirect
from flask import render_template

from datetime import datetime
from functools import wraps

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

base_params = {'domain': config['WEB']['HOST'], 'brand': config['DEFAULT']['BRAND'], 'ws_host': config['WS']['HOST'], 'ws_port': config['WS']['PORT']}

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['JSON_AS_ASCII'] = False


"""
Renders
"""

def get_headers():
	return {'Authorization': 'Bearer {}'.format(session['access_token'])}


def mine():
	return requests.get(get_url('/people/{}/detail'.format(session['id'])), headers=get_headers()).json()


def pjax(template, **params):
	params.update(base_params)
	if 'X-PJAX' in request.headers:
		params['mine'] = {
			'id': session['id'],
			'name': session['name']
		}
		return render_template(template, **params)
	else:
		params['mine'] = mine()['people']
		return render_template("base.html", template=template, **params)


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'id' in session and 'access_token' in session:
			url = get_url('/people/{}/valid'.format(session['id']))
			data = requests.get(url, headers=get_headers()).json()
			if data['ret'] == 1:
				return f(*args, **kwargs)
		return render_template('index.html', **base_params)
	return decorated_function


@app.route('/search', methods=['GET'])
@login_required
def search():
	params = {
		's': request.args.get('s', default=''),
		't': request.args.get('t', default='1'),
		'offset': parse_int(request.args.get('offset', default=''), default=0),
		'limit': parse_int(request.args.get('limit', default=''), default=30),
		'ad': get_ad()
	}
	url = get_url('/search?s={}&t={}&offset={:d}&limit={:d}'.format(params['s'], params['t'], params['offset'], params['limit']))
	data = requests.get(url).json()
	search_route = {
		'1': search_songs,
		'10': search_albums,
		'100': search_artists,
		'1000': search_playlists,
		'0': search_people
	}
	if params['t'] in search_route:
		ret = search_route[params['t']](data)
		ret.update(params)
		return pjax('search.html', **ret)
	else:
		return pjax('404.html')


def search_songs(data):
	ret = {
		'search_template': 'song_list.html',
		'count': data['result']['songCount'] if 'result' in data and 'songCount' in data['result'] else 0,
		'songs': data['result']['songs'] if 'result' in data and 'songs' in data['result'] else [],
		'title': False,
		'page': True
	}
	return ret


def search_albums(data):
	ret = {
		'search_template': 'album_list.html',
		'count': data['result']['albumCount'] if 'result' in data and 'albumCount' in data['result'] else 0,
		'albums': data['result']['albums'] if 'result' in data and 'albums' in data['result'] else []
	}
	return ret


def search_artists(data):
	ret = {
		'search_template': 'artist_list.html',
		'count': data['result']['artistCount'] if 'result' in data and 'artistCount' in data['result'] else 0,
		'artists': data['result']['artists'] if 'result' in data and 'artists' in data['result'] else []
	}
	return ret


def search_playlists(data):
	ret = {
		'search_template': 'playlist_list.html',
		'count': data['result']['playlistCount'] if 'result' in data and 'playlistCount' in data['result'] else 0,
		'playlists': data['result']['playlists'] if 'result' in data and 'playlists' in data['result'] else []
	}
	return ret


def search_people(data):
	ret = {
		'search_template': 'people_list.html',
		'count': data['count'] if 'count' in data else 0,
		'people_list': data['people'] if 'people' in data else []
	}
	return ret


@app.route('/songs/<id>', methods=['GET'])
@login_required
def song(id=''):
	url = get_url('/songs/{}'.format(id))
	song = requests.get(url).json()['songs'][0]
	url = get_url('/lyrics/{}'.format(id))
	data = requests.get(url).json()
	lyric = []
	if 'lrc' in data and 'lyric' in data['lrc']:
		lyric = [re.sub('\[.*\]', '', line) for line in re.split('\n', data['lrc']['lyric'])]
	return pjax('song.html', song=song, lyric=lyric, ad=get_ad())


@app.route('/albums/<id>', methods=['GET'])
@login_required
def album(id=''):
	url = get_url('/albums/{}'.format(id))
	data = requests.get(url).json()
	songs = data['album']['songs'] if 'album' in data and 'songs' in data['album'] else []
	return pjax('album.html', data=data, songs=songs, ad=get_ad())


@app.route('/artists/<id>', methods=['GET'])
@login_required
def artist(id=''):
	url = get_url('/artists/{}'.format(id))
	data = requests.get(url).json()
	return pjax('artist.html', data=data, ad=get_ad())


@app.route('/playlists/<id>', methods=['GET'])
@login_required
def playlist(id=''):
	url = get_url('/playlists/{}'.format(id))
	data = requests.get(url).json()
	songs = data['result']['tracks'] if 'result' in data and 'tracks' in data['result'] else []
	return pjax('playlist.html', data=data, songs=songs, ad=get_ad())


@app.route('/', methods=['GET'])
@app.route('/toplists/', methods=['GET'])
@app.route('/toplists/<id>', methods=['GET'])
@login_required
def toplist(id='3779629'):
	url = get_url('/toplists/{}'.format(id))
	data = requests.get(url).json()
	toplist = {
		'id': id,
		'songs': data['songs'] if 'songs' in data else []
	}
	return pjax('toplist.html', toplist=toplist)


@app.route('/explore/playlists', methods=['GET'])
@app.route('/explore/playlists/<cat>', methods=['GET'])
@login_required
def explore_playlist(cat='全部'):
	params = {
		'cat': cat,
		'offset': parse_int(request.args.get('offset', default=''), default=0),
		'limit': parse_int(request.args.get('limit', default=''), default=30)
	}
	url = get_url('/explore/playlists/{}?offset={:d}&limit={:d}'.format(params['cat'], params['offset'], params['limit']))
	data = requests.get(url).json()
	return pjax('explore_playlist.html', count=data['count'], playlists=data['playlists'], **params)


@app.route('/people/<id>', methods=['GET'])
@login_required
def people(id=''):
	url = get_url('/people/{}'.format(id))
	people = requests.get(url).json()['people']
	return pjax('people.html', people=people, ad=get_ad())


"""
Play and sync related
"""

@app.route('/player', methods=['GET'])
@login_required
def player():
	url = get_url('/people/{}/player'.format(session['id']))
	data = requests.get(url, headers=get_headers()).json()
	return jsonify(**data)


@app.route('/player/playlist', methods=['POST', 'PUT', 'DELETE'])
@login_required
def player_playlist():
	url = get_url('/people/{}/player/playlist'.format(session['id']))
	data = requests.request(request.method, url, headers=get_headers(), data=request.form).json()
	if data['ret'] == 1 and request.method in ('POST', 'PUT'):
		sid = request.form['sid'] if request.method == 'POST' else json.loads(request.form['sids'])[0]
		url = get_url('/people/{}/player'.format(session['id']))
		ret = requests.request('PUT', url, headers=get_headers(), data={'status':'playing', 'sid':sid}).json()
		app.logger.info('update player song {}'.format('success' if 'ret' in ret and ret['ret'] == 1 else 'failed'))
	return jsonify(**data)


@app.route('/player/playlist/<sid>', methods=['DELETE'])
@login_required
def player_playlist_sid(sid=''):
	url = get_url('/people/{}/player/playlist/{}'.format(session['id'], sid))
	data = requests.request(request.method, url, headers=get_headers(), data=request.form).json()
	return jsonify(**data)


@app.route('/notice', methods=['GET'])
@login_required
def notice():
	return pjax('notice.html')


"""
Account related
"""

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
	if request.method == 'GET':
		return render_template('sign_up.html', **base_params)
	else:
		url = get_url('/people')
		payload = {'id': request.form['pid'], 'name': request.form['name'], 'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			return render_template('tips.html', tips='{}，恭喜，注册成功！我们已向{}发送了一封邮件，请尽快登录并激活当前账户。'.format(payload['name'], payload['email']), **base_params)
		else:
			return render_template('tips.html', tips='{}，抱歉，注册失败，请稍候再次尝试。'.format(payload['name']), **base_params)


@app.route('/people/<id>/activation', methods=['GET'])
def activate(id=''):
	url = get_url('/people/{}/activation?code={}'.format(id, request.args.get('code', default='')))
	data = requests.post(url).json()
	if data['ret'] == 1:
		return render_template('tips.html', tips='激活成功！', **base_params)
	else:
		return render_template('tips.html', tips='激活失败……', **base_params)


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
	if request.method == 'GET':
		return render_template('sign_in.html', ret=1, username='', password='', **base_params)
	else:
		url = get_url('/oauth2/tokens')
		payload = {'grant_type': 'password', 'username': request.form['username'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			url = get_url('/people/{}'.format(payload['username']))
			people = requests.get(url).json()['people']
			session['id'] = people['id']
			session['name'] = people['name']
			session['access_token'] = data['access_token']
			return redirect('/')
		else:
			return render_template('sign_in.html', ret=data['ret'], username=payload['username'], password=payload['password'], **base_params)


@app.route('/sign-out', methods=['GET'])
def sign_out():
	session.clear()
	return redirect('/')


"""
Filters
"""

@app.template_filter('date_format_filter')
def date_format_filter(value, format='%Y-%m-%d'):
	return datetime.fromtimestamp(int(value) // 1000).strftime(format)


@app.template_filter('time_format_filter')
def time_format_filter(value, format='%H:%M'):
	seconds = int(value) // 1000
	return '{0:02d}:{0:02d}'.format(seconds // 60, seconds % 60)


@app.template_filter('page_ceil_filter')
def page_ceil_filter(value, max_value=9):
	return min(math.ceil(value), max_value)


"""
Utilities
"""

def parse_int(s, default=0):
	try:
		return int(s)
	except ValueError:
		return default


def get_ad():
	return random.randint(0, 5)


def get_url(resource):
	return 'http://{}/{}{}'.format(config['SERVER']['HOST'], config['WEB']['VERSION'], resource)


"""
Deprecated
"""

@app.route('/api_deprecated/<path:path>', methods=['GET', 'POST'])
def api(path=''):
	if request.method == 'GET':
		url = 'http://{}/{}?{}'.format(config['SERVER']['HOST'], path, '&'.join(['{}={}'.format(key, request.args[key]) for key in request.args]))
		data = requests.get(url).json()
		return jsonify(**data)
	else:
		url = 'http://{}/{}?{}'.format(config['SERVER']['HOST'], path, '&'.join(['{}={}'.format(key, request.args[key]) for key in request.args]))
		post_data = {}
		post_data.update(request.form)
		if 'pid' in session and 'access_token' in session:
			post_data['pid'] = session['pid']
			post_data['access_token'] = session['access_token']
		data = requests.post(url, data=post_data).json()
		return jsonify(**data)



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

