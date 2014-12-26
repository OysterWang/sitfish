#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
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

from pprint import pprint
from datetime import datetime

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

base_params = {'domain': config['WEB']['HOST'], 'brand': config['DEFAULT']['BRAND']}

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['JSON_AS_ASCII'] = False


"""
Foundation
"""

@app.route('/song/<id>', methods=['GET'])
def song(id=''):
	url = 'http://%s/v1/song/%s' % (config['SERVER']['HOST'], id)
	song = requests.get(url).json()['songs'][0]
	url = 'http://%s/v1/lyric/%s' % (config['SERVER']['HOST'], id)
	lyric = [re.sub('\[.*\]', '', line) for line in re.split('\n', requests.get(url).json()['lrc']['lyric'])]
	return pjax('song.html', song=song, lyric=lyric, ad=random.randint(0, 5))


@app.route('/album/<id>', methods=['GET'])
def album(id=''):
	url = 'http://%s/v1/album/%s' % (config['SERVER']['HOST'], id)
	data = requests.get(url).json()
	return pjax('album.html', data=data, songs=data['album']['songs'], ad=random.randint(0, 5))


@app.route('/playlist/<id>', methods=['GET'])
def playlist(id=''):
	url = 'http://%s/v1/playlist/%s' % (config['SERVER']['HOST'], id)
	data = requests.get(url).json()
	return pjax('playlist.html', data=data, songs=data['result']['tracks'], ad=random.randint(0, 5))


@app.route('/', methods=['GET'])
@app.route('/toplist/', methods=['GET'])
@app.route('/toplist/<id>', methods=['GET'])
def toplist(id='3778678'):
	url = 'http://%s/v1/toplist/%s' % (config['SERVER']['HOST'], id)
	data = requests.get(url).json()
	return pjax('toplist.html', id=id, songs=data['songs'])


@app.route('/explore/playlist', methods=['GET'])
@app.route('/explore/playlist/cat', methods=['GET'])
@app.route('/explore/playlist/cat/<cat>', methods=['GET'])
def explore_playlist(cat='全部'):
	offset = parse_int(request.args.get('offset', default=''), default=0)
	limit = parse_int(request.args.get('limit', default=''), default=30)
	url = 'http://%s/v1/explore/playlist/cat/%s?offset=%d&limit=%d' % (config['SERVER']['HOST'], cat, offset, limit)
	data = requests.get(url).json()
	return pjax('explore_playlist.html', playlists=data['playlists'])


@app.route('/player', methods=['GET', 'POST'])
def player_songs():
	if request.method == 'GET':
		pass
	else:
		pass


"""
People management
"""

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
	if request.method == 'GET':
		return render_template('sign_up.html', **base_params)
	else:
		url = 'http://%s/v1/sign-up' % config['SERVER']['HOST']
		payload = {'pid': request.form['pid'], 'name': request.form['name'], 'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			return render_template('tips.html', tips='%s，恭喜，注册成功！我们已向%s发送了一封邮件，请尽快登录并激活当前账户。' % (payload['name'], payload['email']), **base_params)
		else:
			return render_template('tips.html', tips='%s，抱歉，注册失败，请稍候再次尝试。' % payload['name'], **base_params)


@app.route('/activate/<pid>', methods=['GET'])
def activate(pid=''):
	url = 'http://%s/v1/activate/%s?code=%s' % (config['SERVER']['HOST'], pid, request.args.get('code', default=''))
	data = requests.get(url).json()
	if data['ret'] == 1:
		return render_template('tips.html', tips='激活成功！', **base_params)
	else:
		return render_template('tips.html', tips='激活失败……', **base_params)


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
	if request.method == 'GET':
		return render_template('sign_in.html', ret=1, email='', password='', **base_params)
	else:
		url = 'http://%s/v1/sign-in' % config['SERVER']['HOST']
		payload = {'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			session['pid'] = data['people']['pid']
			session['access_token'] = data['people']['access_token']
			return redirect('/')
		else:
			return render_template('sign_in.html', ret=data['ret'], email=payload['email'], password=payload['password'], **base_params)


@app.route('/sign-out', methods=['GET'])
def sign_out():
	session.clear()
	return redirect('/')


@app.route('/api/<path:path>', methods=['GET', 'POST'])
def api(path=''):
	if request.method == 'GET':
		url = 'http://%s/%s?%s' % (config['SERVER']['HOST'], path, '&'.join(['%s=%s' % (key, request.args[key]) for key in request.args]))
		data = requests.get(url).json()
		return jsonify(**data)
	else:
		url = 'http://%s/%s?%s' % (config['SERVER']['HOST'], path, '&'.join(['%s=%s' % (key, request.args[key]) for key in request.args]))
		data = requests.post(url, data=request.form).json()
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
	return '%02d:%02d' % (seconds // 60, seconds % 60)


"""
Utilities
"""

def parse_int(s, default=0):
	try:
		return int(s)
	except ValueError:
		return default


def pjax(template, **params):
	data = validate()
	if data is not None and data['ret'] == 1:
		params.update(data['people'])
		if 'X-PJAX' in request.headers:
			return render_template(template, **dict(base_params, **params))
		else:
			return render_template("base.html", template=template, **dict(base_params, **params))
	else:
		return render_template('index.html', **base_params)


def validate():
	if 'pid' in session and 'access_token' in session:
		url = 'http://%s/v1/validate' % config['SERVER']['HOST']
		payload = {'pid': session['pid'], 'access_token': session['access_token']}
		return requests.post(url, data=payload).json()
	return None



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

