#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import codecs
import requests
import traceback
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
from mongoengine.errors import *


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
		data = {'count': People.objects(id__contains=s).count(), 'people': []}
		for people in People.objects(id__contains=s).skip(offset).limit(limit):
			data['people'].append(people.public_json())
	else:
		url = 'http://music.163.com/api/search/pc'
		payload = {'s': s, 'type': t, 'offset': offset, 'total': 'true', 'limit': limit}
		data = requests.post(url, data=payload, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1
@app.route('/v1/songs/<ids>', methods=['GET'])
def songs(ids=''):
	ids = re.split(',', ids)
	url = 'http://music.163.com/api/song/detail?ids={}'.format(ids)
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 10
@app.route('/v1/albums/<id>', methods=['GET'])
def albums(id=''):
	url = 'http://music.163.com/api/album/{}'.format(id)
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 100
@app.route('/v1/artists/<id>', methods=['GET'])
def artists(id=''):
	url = 'http://music.163.com/api/artist/albums/{}?limit={0:d}'.format(id, app.config['LIMIT'])
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1000
@app.route('/v1/playlists/<id>', methods=['GET'])
def playlists(id=''):
	url = 'http://music.163.com/api/playlist/detail?id={}'.format(id)
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1006
@app.route('/v1/lyrics/<id>', methods=['GET'])
def lyrics(id=''):
	url = 'http://music.163.com/api/song/lyric?id={}&lv=-1&kv=-1&tv=-1'.format(id)
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


@app.route('/v1/toplists/<id>', methods=['GET'])
def toplists(id=''):
	data = {'songs': []}
	url = 'http://music.163.com/discover/toplist?id={}'.format(id)
	soup = BeautifulSoup(requests.get(url).content)
	table = soup.find('tbody', id='tracklist')
	if table:
		ids = re.findall(r'/song\?id=(\d+)', str(table))
		ids = sorted(set(ids),key=ids.index)
		url = 'http://music.163.com/api/song/detail?ids=[{}]'.format(','.join(ids))
		data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


"""
Explore related
"""

@app.route('/v1/explore/playlists', methods=['GET'])
@app.route('/v1/explore/playlists/<cat>', methods=['GET'])
def explore_playlists_cat(cat='全部'):
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=35)
	data = {'count': 0, 'playlists': []}
	url = 'http://music.163.com/discover/playlist/?cat={}&offset={0:d}&limit={0:d}'.format(cat, offset, limit)
	soup = BeautifulSoup(requests.get(url).content)
	pages = soup.findAll('a', class_='zpgi')
	if len(pages) > 0:
		page_num = parse_int(pages[-1].text)
		data['count'] = limit * page_num
	ul = soup.find('ul', id='m-pl-container')
	if ul:
		for li in ul.findAll('li'):
			if li.div and li.div.img and li.div.a:
				data['playlists'].append({'id': re.split('id=', li.div.a['href'])[-1], 'name': li.div.a['title'], 'coverImgUrl': re.split('\?param', li.div.img['src'])[0]})
	return jsonify(**data)


"""
Account related
"""

@app.route('/v1/people', methods=['POST'])
def people():
	data = {'ret': 0}
	try:
		people = People.new(id=request.form['id'], name=request.form['name'], email=request.form['email'], password=request.form['password']).save(force_insert=True)
		brand = config['DEFAULT']['BRAND']
		url = 'http://{}/people/{}/activation?code={}'.format(config['WEB']['HOST'], people.id, people.activation.code)
		html = '<p>亲爱的{}：</p><p>欢迎加入{}！</p><p>请点击下面的链接完成注册：</p><p><a href="{}" target="_blank">{}</a></p><p>如果以上链接无法点击，请将上面的地址复制到你的浏览器(如Chrome)的地址栏进入{}。</p><p>{}</p>'.format(people.name, brand, url, url, brand, brand)
		send_activation('{}账户激活'.format(brand), html, people.email)
		data['ret'] = 1
	except NotUniqueError:
		app.logger.info('This id "{}" has been taken.'.format(request.form['id']))
	except:
		app.logger.error(traceback.format_exc())
	return jsonify(**data)


@app.route('/v1/people/<id>/activation', methods=['GET'])
def activate(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people and people.activation.code == request.args.get('code', default=''):
		if not people.activation.status:
			people.activation.time = datetime.datetime.now()
			people.activation.status = True
			people.save()
		data['ret'] = 1
	return jsonify(**data)


"""
Detailed info
"""

# TYPE - 0
@app.route('/v1/people/<id>', methods=['GET'])
def people_id(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first() if id != '' else People.objects(email=request.args.get('email', default='')).first()
	if people:
		data['ret'] = 1
		data['people'] = people.public_json()
	return jsonify(**data)

@app.route('/v1/player/<id>', methods=['GET'])
def player(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		data['ret'] = 1
		data['player'] = people.player.json() if people.player else ''
	return jsonify(**data)


@app.route('/v1/player/playlist/add', methods=['POST'])
def player_playlist_add():
	data = {'ret': 0}
	people = People.objects(id=request.form['id']).first()
	if people:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			ids = set([song['id'] for song in people.player.playlist])
			for song in json.loads(request.form['songs']):
				if song['id'] not in ids:
					obj = Song(id=song['id'], name=song['name'], source=song['source'], img=song['img'], time=song['time'], artist_id=song['artist_id'], artist_name=song['artist_name'])
					people.player.update(push__playlist=obj)
			data['player'] = People.objects(id=request.form['id']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/replace', methods=['POST'])
def player_playlist_replace():
	data = {'ret': 0}
	people = People.objects(id=request.form['id']).first()
	if people:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			people.player.update(set__playlist=[])
			for song in json.loads(request.form['songs']):
				obj = Song(id=song['id'], name=song['name'], source=song['source'], img=song['img'], time=song['time'], artist_id=song['artist_id'], artist_name=song['artist_name'])
				people.player.update(push__playlist=obj)
			data['player'] = People.objects(id=request.form['id']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/delete', methods=['POST'])
def player_playlist_delete():
	data = {'ret': 0}
	people = People.objects(id=request.form['id']).first()
	if people:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			for id in json.loads(request.form['ids']):
				people.player.update(pull__playlist={'id': id})
			data['player'] = People.objects(id=request.form['id']).first().player.json();
	return jsonify(**data)


@app.route('/v1/player/playlist/clear', methods=['POST'])
def player_playlist_clear():
	data = {'ret': 0}
	people = People.objects(id=request.form['id']).first()
	if people:
		if people.access_token == request.form['access_token']:
			data['ret'] = 1
			people.player.update(set__playlist=[])
			data['player'] = People.objects(id=request.form['id']).first().player.json();
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
Tokens
"""

@app.route('/v1/oauth2/tokens', methods=['POST'])
def sign_in():
	data = {'ret': 0}
	people = People.objects(id=request.form['username']).first()
	if people:
		if not people.activation.status:
			data['ret'] = -1
		elif people.check_password(request.form['password']):
			token = Token.new(people.id, people.activation.code)
			people.update(push__tokens=token)
			data['ret'] = 1
			data['access_token'] = token.access_token
			data['token_type'] = token.token_type
			data['expire_in'] = token.expire_in
	return jsonify(**data)


"""
Utilities
"""

def parse_int(s, default=0):
	try:
		return int(s)
	except ValueError:
		return default


def send_activation(subject, html, recipient):
	mail.send(Message(subject, html=html, sender=(config['DEFAULT']['BRAND'], config['MAIL']['USERNAME']), recipients=[recipient]))



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['SERVER']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

