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
Session permanent
"""

@app.before_request
def make_session_permanent():
    session.permanent = True


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
		'limit': parse_int(request.args.get('limit', default=''), default=30)
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
	return pjax('song.html', song=song, lyric=lyric)


@app.route('/albums/<id>', methods=['GET'])
@login_required
def album(id=''):
	url = get_url('/albums/{}'.format(id))
	data = requests.get(url).json()
	songs = data['album']['songs'] if 'album' in data and 'songs' in data['album'] else []
	return pjax('album.html', data=data, songs=songs)


@app.route('/artists/<id>', methods=['GET'])
@login_required
def artist(id=''):
	url = get_url('/artists/{}'.format(id))
	data = requests.get(url).json()
	return pjax('artist.html', data=data)


@app.route('/playlists/<id>', methods=['GET'])
@login_required
def playlist(id=''):
	url = get_url('/playlists/{}'.format(id))
	data = requests.get(url).json()
	songs = data['result']['tracks'] if 'result' in data and 'tracks' in data['result'] else []
	return pjax('playlist.html', data=data, songs=songs)


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
	return pjax('people.html', people=people)


@app.route('/notice', methods=['GET'])
@login_required
def notice():
	url = get_url('/people/{}/requests'.format(session['id']))
	data = requests.get(url, headers=get_headers()).json()
	reqs = data['receive']
	id_name_dict = {}
	for req in reqs:
		if req['source'] not in id_name_dict:
			json = requests.get(get_url('/people/{}'.format(req['source']))).json()
			if json['ret'] == 1:
				id_name_dict[req['source']] = json['people']['name']
		req['source_name'] = id_name_dict[req['source']] if req['source'] in id_name_dict else ''
	return pjax('notice.html', reqs=reqs)


"""
Data API
"""

@app.route('/lyrics/<sid>', methods=['GET'])
def lyrics(sid=''):
	data = {'name': '', 'lyrics': []}
	resp = requests.get(get_url('/songs/{}'.format(sid)))
	if resp.status_code == 200:
		json = resp.json()
		data['name'] = json['songs'][0]['name'] if 'songs' in json else ''
	resp = requests.get(get_url('/lyrics/{}'.format(sid)))
	if resp.status_code == 200:
		json = resp.json()
		data['lyrics'] = [re.sub('\[.*\]', '', line) for line in re.split('\n', json['lrc']['lyric'])] if 'lrc' in json else []
	data['status_code'] = resp.status_code
	return jsonify(**data)


"""
Play and sync related
"""

@app.route('/player', methods=['GET', 'PUT'])
@login_required
def player():
	data = {}
	url = get_url('/people/{}/player'.format(session['id']))
	if request.method == 'GET':
		data = requests.get(url, headers=get_headers()).json()
	else:
		data = requests.request('PUT', url, headers=get_headers(), data={'status':request.form['status'], 'sid':request.form['sid']}).json()
	return jsonify(**data)


@app.route('/player/playlist', methods=['POST', 'PUT', 'DELETE'])
@login_required
def player_playlist():
	url = get_url('/people/{}/player/playlist'.format(session['id']))
	data = requests.request(request.method, url, headers=get_headers(), data=request.form).json()
	if data['ret'] == 1 and request.method in ('POST', 'PUT'):
		sid = request.form['sid'] if request.method == 'POST' else json.loads(request.form['sids'])[0]
		url = get_url('/people/{}/player'.format(session['id']))
		data = requests.request('PUT', url, headers=get_headers(), data={'status':'playing', 'sid':sid}).json()
		app.logger.info('update player song {}'.format('success' if 'ret' in data and data['ret'] == 1 else 'failed'))
	return jsonify(**data)


@app.route('/player/playlist/<sid>', methods=['DELETE'])
@login_required
def player_playlist_sid(sid=''):
	url = get_url('/people/{}/player/playlist/{}'.format(session['id'], sid))
	data = requests.request(request.method, url, headers=get_headers(), data=request.form).json()
	return jsonify(**data)


"""
Friends related
"""

@app.route('/requests', methods=['GET', 'POST', 'DELETE'])
@login_required
def requests_api():
	data = {}
	url = get_url('/people/{}/requests'.format(session['id']))
	if request.method == 'GET':
		data = requests.get(url, headers=get_headers()).json()
	elif request.method == 'POST':
		data = requests.post(url, headers=get_headers(), data={'id': request.form['id']}).json()
	else:
		data = requests.request('DELETE', url, headers=get_headers(), data={'id': request.form['id']}).json()
	return jsonify(**data)


@app.route('/connect/<id>', methods=['GET'])
@login_required
def connect(id=''):
	url = get_url('/people/{}/connect/{}'.format(session['id'], id))
	data = requests.get(url, headers=get_headers()).json()
	return jsonify(**data)


@app.route('/disconnect/<id>', methods=['GET'])
@login_required
def disconnect(id=''):
	url = get_url('/people/{}/disconnect/{}'.format(session['id'], id))
	data = requests.get(url, headers=get_headers()).json()
	return jsonify(**data)


@app.route('/sign-out', methods=['GET'])
@login_required
def sign_out():
	url = get_url('/people/{}/sign-out'.format(session['id']))
	data = requests.get(url, headers=get_headers()).json()
	session.clear()
	return redirect('/')


"""
Account related
"""

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
	if request.method == 'GET':
		return render_template('sign_up.html', **base_params)
	else:
		url = get_url('/people')
		payload = {'id': request.form['id'], 'name': request.form['name'], 'email': request.form['email'], 'password': request.form['password']}
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


@app.route('/check/<id>', methods=['GET'])
def check(id=''):
	url = get_url('/people/{}'.format(id))
	data = requests.get(url).json()
	return jsonify(**data)


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


def get_url(resource):
	return 'http://{}/{}{}'.format(config['SERVER']['HOST'], config['WEB']['VERSION'], resource)



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

