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

@app.route('/', methods=['GET'])
def host():
	return redirect('/v1')


@app.route('/v1', methods=['GET'])
def index():
	return render_template('v1.html', version='v1', host=config['SERVER']['HOST'], brand=config['DEFAULT']['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'])


"""
Resource related
"""

@app.route('/v1/search', methods=['GET'])
def search():
	s = request.args.get('s', default='')
	t = request.args.get('t', default='')
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=app.config['LIMIT'])
	data = {}
	if t == '0':
		data = {'people': []}
		for people in People.objects(pid__contains=s).limit(limit):
			data['people'].append(people.public_json())
	else:
		url = 'http://music.163.com/api/search/pc'
		payload = {'s': s, 'type': t, 'offset': offset, 'total': 'true', 'limit': limit}
		data = requests.post(url, data=payload, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 0
@app.route('/v1/people/<id>', methods=['GET'])
def people(id=''):
	data = {'ret': 0}
	people = People.objects(pid=id).first()
	if people is not None:
		data['ret'] = 1
		data['people'] = people.public_json()
	return jsonify(**data)


# TYPE - 1
@app.route('/v1/song/<ids>', methods=['GET'])
def song(ids=''):
	ids = re.split(',', ids)
	url = 'http://music.163.com/api/song/detail?ids=%s' % ids
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 10
@app.route('/v1/album/<id>', methods=['GET'])
def album(id=''):
	url = 'http://music.163.com/api/album/%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 100
@app.route('/v1/artist/<id>', methods=['GET'])
def artist(id=''):
	url = 'http://music.163.com/api/artist/albums/%s?limit=%d' % (id, app.config['LIMIT'])
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1000
@app.route('/v1/playlist/<id>', methods=['GET'])
def playlist(id=''):
	url = 'http://music.163.com/api/playlist/detail?id=%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1006
@app.route('/v1/lyric/<id>', methods=['GET'])
def lyric(id=''):
	url = 'http://music.163.com/api/song/lyric?id=%s&lv=-1&kv=-1&tv=-1' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


@app.route('/v1/toplist/<id>', methods=['GET'])
def toplist(id=''):
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
Explore related
"""

@app.route('/v1/explore/playlist/cat', methods=['GET'])
@app.route('/v1/explore/playlist/cat/<cat>', methods=['GET'])
def explore_playlist_cat(cat='全部'):
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=35)
	data = {'playlists': []}
	url = 'http://music.163.com/discover/playlist/?cat=%s&offset=%d&limit=%d' % (cat, offset, limit)
	soup = BeautifulSoup(requests.get(url).content)
	ul = soup.find('ul', id='m-pl-container')
	if ul is not None:
		for li in ul.findAll('li'):
			if li.div is not None and li.div.img is not None and li.div.a is not None:
				data['playlists'].append({'plid': re.split('id=', li.div.a['href'])[-1], 'name': li.div.a['title'], 'img': li.div.img['src']})
	return jsonify(**data)


"""
Account related
"""

@app.route('/v1/exist', methods=['GET'])
def count():
	s = request.args.get('s', default='')
	t = request.args.get('t', default='0') # pid:0, email:1
	data = {'exist': 0}
	if t == '0':
		if People.objects(pid=s).count() > 0:
			data['exist'] = 1
	elif t == '1':
		if People.objects(email=s).count() > 0:
			data['exist'] = 1
	return jsonify(**data)


@app.route('/v1/sign-up', methods=['POST'])
def sign_up():
	data = {'ret': 0}
	try:
		people = People.create(pid=request.form['pid'], name=request.form['name'], email=request.form['email'], password=request.form['password'])
		people.password = sha(people.password, people.activation_code)
		people.save(force_insert=True)
		brand = config['DEFAULT']['BRAND']
		url = 'http://%s/activate/%s?code=%s' % (config['WEB']['HOST'], people.pid, people.activation_code)
		html = '<p>亲爱的%s：</p><p>欢迎加入%s！</p><p>请点击下面的链接完成注册：</p><p><a href="%s" target="_blank">%s</a></p><p>如果以上链接无法点击，请将上面的地址复制到你的浏览器(如Chrome)的地址栏进入%s。</p><p>%s</p>' % (people.name, brand, url, url, brand, brand)
		send_activation('%s账户激活' % brand, html, people.email)
		data['ret'] = 1
	except:
		pass
	return jsonify(**data)


@app.route('/v1/activate/<pid>', methods=['GET'])
def activate(pid=''):
	data = {'ret': 0}
	code = request.args.get('code', default='')
	people = People.objects(pid=pid, activation_code=code).first()
	if people is not None:
		if people.activation is not True:
			people.activation = True
			people.save()
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/sign-in', methods=['POST'])
def sign_in():
	data = {'ret': 0}
	people = People.objects(email=request.form['email']).first()
	if people is not None:
		if not people.activation:
			data['ret'] = -1
		elif people.password == sha(request.form['password'], people.activation_code):
			people.access_token = sha(people.pid, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
			people.save()
			data['ret'] = 1
			data['people'] = people.private_json()
	return jsonify(**data)


@app.route('/v1/validate', methods=['POST'])
def validate():
	data = {'ret': 0}
	people = People.objects(pid=request.form['pid']).first()
	if people is not None:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			data['people'] = people.private_json()
	return jsonify(**data)


"""
Player related
"""

@app.route('/v1/player/<id>', methods=['GET'])
def player(id=''):
	data = {'ret': 0}
	people = People.objects(pid=id).first()
	if people is not None:
		data['ret'] = 1
		data['player'] = people.player.json() if people.player is not None else ''
	return jsonify(**data)


@app.route('/v1/player/playlist/add', methods=['POST'])
def player_playlist_add():
	data = {'ret': 0}
	people = People.objects(pid=request.form['pid']).first()
	if people is not None:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			sids = set([song['sid'] for song in people.player.playlist])
			for song in json.loads(request.form['songs']):
				if song['sid'] not in sids:
					obj = Song(sid=song['sid'], name=song['name'], source=song['source'], img=song['img'], time=song['time'], artist_id=song['artist_id'], artist_name=song['artist_name'])
					people.player.update(push__playlist=obj)
			data['player'] = People.objects(pid=request.form['pid']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/replace', methods=['POST'])
def player_playlist_replace():
	data = {'ret': 0}
	people = People.objects(pid=request.form['pid']).first()
	if people is not None:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			people.player.update(set__playlist=[])
			for song in json.loads(request.form['songs']):
				obj = Song(sid=song['sid'], name=song['name'], source=song['source'], img=song['img'], time=song['time'], artist_id=song['artist_id'], artist_name=song['artist_name'])
				people.player.update(push__playlist=obj)
			data['player'] = People.objects(pid=request.form['pid']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/delete', methods=['POST'])
def player_playlist_delete():
	data = {'ret': 0}
	people = People.objects(pid=request.form['pid']).first()
	if people is not None:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			for sid in json.loads(request.form['sids']):
				people.player.update(pull__playlist={'sid': sid})
			data['player'] = People.objects(pid=request.form['pid']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/clear', methods=['POST'])
def player_playlist_clear():
	data = {'ret': 0}
	people = People.objects(pid=request.form['pid']).first()
	if people is not None:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			people.player.update(set__playlist=[])
			data['player'] = People.objects(pid=request.form['pid']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/play', methods=['POST'])
def player_play():
	return 'TODO'


@app.route('/v1/player/pause', methods=['POST'])
def player_pause():
	return 'TODO'


@app.route('/v1/player/skip', methods=['POST'])
def player_skip():
	return 'TODO'


"""
Utilities
"""

def parse_int(s, default=0):
	try:
		return int(s)
	except ValueError:
		return default


def sha(*params):
	h = hashlib.new(config['DB']['SHA'])
	h.update(' '.join(params).encode('utf-8'))
	return h.hexdigest()


def send_activation(subject, html, recipient):
	mail.send(Message(subject, html=html, sender=(config['DEFAULT']['BRAND'], config['MAIL']['USERNAME']), recipients=[recipient]))



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['SERVER']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

