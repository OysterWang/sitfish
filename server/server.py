#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import codecs
import hashlib
import requests
import configparser

from bs4 import BeautifulSoup
from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import render_template
from database import *
from functools import wraps
from flask.ext.mail import Mail
from flask.ext.mail import Message

from pprint import pprint

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

app = Flask(__name__)

app.config['HEADERS'] = {'Referer': 'http://music.163.com'}
app.config['OFFSET'] = 0
app.config['LIMIT'] = 100
app.config['JSON_AS_ASCII'] = False

app.config['MAIL_SERVER'] = config['MAIL']['SERVER']
app.config['MAIL_PORT'] = int(config['MAIL']['PORT'])
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = config['MAIL']['USERNAME']
app.config['MAIL_PASSWORD'] = config['MAIL']['PASSWORD']

mail = Mail(app)


"""
API website related
"""

@app.route('/', methods=['get'])
def host():
	return redirect('/v1')


@app.route('/v1', methods=['get'])
def index():
	return render_template('v1.html', version='v1', host=config['SERVER']['HOST'], brand=config['DEFAULT']['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'])


"""
Resource related
"""

@app.route('/v1/search', methods=['get'])
def search():
	def parse_int(s, default=0):
		try:
			return int(s)
		except ValueError:
			return default
	s = request.args.get('s', default='')
	t = request.args.get('t', default='')
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=app.config['LIMIT'])
	data = {}
	if t == '0':
		data = {'users': []}
		for user in User.objects(uid__contains=s).limit(limit):
			data['users'].append(user.public_json())
	else:
		url = 'http://music.163.com/api/search/pc'
		payload = {'s': s, 'type': t, 'offset': offset, 'total': 'true', 'limit': limit}
		data = requests.post(url, data=payload, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 0
@app.route('/v1/users/<id>', methods=['get'])
def users(id=''):
	data = {'ret': 0}
	user = User.objects(uid=id).first()
	if user is not None:
		data['ret'] = 1
		data['user'] = user.public_json()
	return jsonify(**data)


# TYPE - 1
@app.route('/v1/songs', methods=['get'])
def songs():
	ids = request.args.get('ids', default='[]')
	url = 'http://music.163.com/api/song/detail?ids=%s' % ids
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 10
@app.route('/v1/albums/<id>', methods=['get'])
def albums(id=''):
	url = 'http://music.163.com/api/album/%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 100
@app.route('/v1/artists/<id>', methods=['get'])
def artists(id=''):
	url = 'http://music.163.com/api/artist/albums/%s?limit=%d' % (id, app.config['LIMIT'])
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1000
@app.route('/v1/playlists/<id>', methods=['get'])
def playlists(id=''):
	url = 'http://music.163.com/api/playlist/detail?id=%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1006
@app.route('/v1/lyrics/<id>', methods=['get'])
def lyrics(id=''):
	url = 'http://music.163.com/api/song/lyric?id=%s&lv=-1&kv=-1&tv=-1' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


@app.route('/v1/toplists/<id>', methods=['get'])
def toplists(id=''):
	data = {'songs': []}
	url = 'http://music.163.com/discover/toplist?id=%s' % id
	soup = BeautifulSoup(requests.get(url).content)
	table = soup.find('tbody', id='tracklist')
	if table is not None:
		ids = re.findall(r'/song\?id=(\d+)', str(table))
		ids = sorted(set(ids),key=ids.index)
		url = 'http://music.163.com/api/song/detail?ids=[%s]' % ','.join(ids)
		data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


"""
Account related
"""

@app.route('/v1/exist', methods=['get'])
def count():
	s = request.args.get('s', default='')
	t = request.args.get('t', default='0') # uid:0, email:1
	data = {'exist': 0}
	if t == '0':
		if User.objects(uid=s).count() > 0:
			data['exist'] = 1
	elif t == '1':
		if User.objects(email=s).count() > 0:
			data['exist'] = 1
	return jsonify(**data)


@app.route('/v1/sign-up', methods=['post'])
def sign_up():
	data = {'ret': 0}
	try:
		user = User.create(uid=request.form['uid'], name=request.form['name'], email=request.form['email'], password=request.form['password'])
		user.password = sha(user.password, user.activation_code)
		user.save(force_insert=True)
		brand = config['DEFAULT']['BRAND']
		url = 'http://%s/activate/%s?code=%s' % (config['WEB']['HOST'], user.uid, user.activation_code)
		html = '<p>亲爱的%s：</p><p>欢迎加入%s！</p><p>请点击下面的链接完成注册：</p><p><a href="%s" target="_blank">%s</a></p><p>如果以上链接无法点击，请将上面的地址复制到你的浏览器(如Chrome)的地址栏进入%s。</p><p>%s</p>' % (user.name, brand, url, url, brand, brand)
		send_activation('%s账户激活' % brand, html, user.email)
		data['ret'] = 1
	except:
		pass
	return jsonify(**data)


@app.route('/v1/activate/<uid>', methods=['get'])
def activate(uid=''):
	data = {'ret': 0}
	code = request.args.get('code', default='')
	user = User.objects(uid=uid, activation_code=code).first()
	if user is not None:
		if user.activation is not True:
			user.activation = True
			user.save()
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/sign-in', methods=['post'])
def sign_in():
	data = {'ret': 0}
	user = User.objects(email=request.form['email']).first()
	if user is not None:
		if not user.activation:
			data['ret'] = -1
		elif user.password == sha(request.form['password'], user.activation_code):
			user.access_token = sha(user.uid, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			user.save()
			data['ret'] = 1
			data['user'] = user.private_json()
	return jsonify(**data)


@app.route('/v1/validate', methods=['post'])
def validate():
	data = {'ret': 0}
	user = User.objects(uid=request.form['uid']).first()
	if user is not None:
		if user.access_token == request.form['access_token']:
			data['ret'] = 1
			data['user'] = user.private_json()
	return jsonify(**data)


"""
Player related
"""

@app.route('/v1/players/<id>', methods=['get'])
def players(id=''):
	data = {'ret': 0}
	user = User.objects(uid=id).first()
	if user is not None:
		data['ret'] = 1
		data['player'] = user.player.json()
	return jsonify(**data)


@app.route('/v1/player/playlist/add', methods=['post'])
def playlist_add():
	data = {'ret': 0}
	user = User.objects(uid=request.form['uid']).first()
	if user is not None:
		if user.access_token == request.form['access_token']:
			data['ret'] = 1
			sids = set([song['sid'] for song in user.player.playlist])
			for song in json.loads(request.form['songs']):
				if song['sid'] not in sids:
					obj = Song(sid=song['sid'], name=song['name'], source=song['source'], img=song['img'], artist_id=song['artist_id'], artist_name=song['artist_name'])
					user.player.update(add_to_set__playlist=[obj, ])
			data['player'] = User.objects(uid=request.form['uid']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/replace', methods=['post'])
def playlist_replace():
	return 'TODO'


@app.route('/v1/player/playlist/delete', methods=['post'])
def playlist_delete():
	return 'TODO'


@app.route('/v1/player/playlist/clear', methods=['post'])
def playlist_clear():
	return 'TODO'


@app.route('/v1/player/play', methods=['post'])
def player_play():
	return 'TODO'


@app.route('/v1/player/pause', methods=['post'])
def player_pause():
	return 'TODO'


@app.route('/v1/player/skip', methods=['post'])
def player_skip():
	return 'TODO'


"""
Utilities
"""

def sha(*params):
	h = hashlib.new(config['DB']['SHA'])
	h.update(' '.join(params).encode('utf-8'))
	return h.hexdigest()


def send_activation(subject, html, recipient):
	mail.send(Message(subject, html=html, sender=(config['DEFAULT']['BRAND'], config['MAIL']['USERNAME']), recipients=[recipient]))



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['SERVER']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

