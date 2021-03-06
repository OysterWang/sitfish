#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../database')
from database import *
from mongoengine.errors import *

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
from flask import Response
from flask import render_template
from functools import wraps
from flask.ext.mail import Mail
from flask.ext.mail import Message


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
API website template related
"""

@app.route('/', methods=['GET'])
def host():
	return redirect('/v1')


@app.route('/v1', methods=['GET'])
def index():
	access_token = 'ISAQwbJyJEwZAM5krsy1IragDVw6ZO7lsZ0kjG+5/VmM+QEaWIGmugqxjNYbdmByrKOvnLYURy1Us+rU7sxIUiq4ZG7XzeU='
	u = People.objects(id='wuzang').first()
	if u and len(u.tokens) > 0:
		access_token = u.tokens[-1].access_token
	return render_template('v1.html', version='v1', host=config['SERVER']['HOST'], brand=config['DEFAULT']['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'], access_token=access_token)


"""
Music lib related
"""

@app.route('/v1/search', methods=['GET'])
def search():
	data = {}
	s = request.args.get('s', default='')
	t = request.args.get('t', default='')
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=app.config['LIMIT'])
	if t == '0':
		data = {'count': People.objects(id__contains=s).count(), 'people': []}
		for people in People.objects(id__contains=s).skip(offset).limit(limit):
			data['people'].append(people.json())
	else:
		url = 'http://music.163.com/api/search/pc'
		payload = {'s': s, 'type': t, 'offset': offset, 'total': 'true', 'limit': limit}
		resp = requests.post(url, data=payload, headers=app.config['HEADERS'])
		if resp.status_code == 200:
			data = resp.json()
		data['status_code'] = resp.status_code
	return jsonify(**data)


# TYPE - 1
@app.route('/v1/songs/<ids>', methods=['GET'])
def songs(ids=''):
	return jsonify(**get_songs(re.split(',', ids)))


def get_songs(ids=[]):
	data = {}
	url = 'http://music.163.com/api/song/detail?ids={}'.format(ids)
	resp = requests.get(url, headers=app.config['HEADERS'])
	if resp.status_code == 200:
		data = resp.json()
	data['status_code'] = resp.status_code
	return data


# TYPE - 10
@app.route('/v1/albums/<id>', methods=['GET'])
def albums(id=''):
	data = {}
	url = 'http://music.163.com/api/album/{}'.format(id)
	resp = requests.get(url, headers=app.config['HEADERS'])
	if resp.status_code == 200:
		data = resp.json()
	data['status_code'] = resp.status_code
	return jsonify(**data)


# TYPE - 100
@app.route('/v1/artists/<id>', methods=['GET'])
def artists(id=''):
	data = {}
	url = 'http://music.163.com/api/artist/albums/{}?limit={:d}'.format(id, app.config['LIMIT'])
	resp = requests.get(url, headers=app.config['HEADERS'])
	if resp.status_code == 200:
		data = resp.json()
	data['status_code'] = resp.status_code
	return jsonify(**data)


# TYPE - 1000
@app.route('/v1/playlists/<id>', methods=['GET'])
def playlists(id=''):
	data = {}
	url = 'http://music.163.com/api/playlist/detail?id={}'.format(id)
	resp = requests.get(url, headers=app.config['HEADERS'])
	if resp.status_code == 200:
		data = resp.json()
	data['status_code'] = resp.status_code
	return jsonify(**data)


# TYPE - 1006
@app.route('/v1/lyrics/<id>', methods=['GET'])
def lyrics(id=''):
	data = {}
	url = 'http://music.163.com/api/song/lyric?id={}&lv=-1&kv=-1&tv=-1'.format(id)
	resp = requests.get(url, headers=app.config['HEADERS'])
	if (resp.status_code == 200):
		data = resp.json()
	data['status_code'] = resp.status_code
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
		resp = requests.get(url, headers=app.config['HEADERS'])
		if resp.status_code == 200:
			data = resp.json()
		data['status_code'] = resp.status_code
	return jsonify(**data)


"""
Explore related
"""

@app.route('/v1/explore/playlists', methods=['GET'])
@app.route('/v1/explore/playlists/<cat>', methods=['GET'])
def explore_playlists_cat(cat='全部'):
	data = {'count': 0, 'playlists': []}
	offset = parse_int(request.args.get('offset', default=''), default=app.config['OFFSET'])
	limit = parse_int(request.args.get('limit', default=''), default=35)
	url = 'http://music.163.com/discover/playlist/?cat={}&offset={:d}&limit={:d}'.format(cat, offset, limit)
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
		app.logger.info('New register user {}'.format(people.id))
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


@app.route('/v1/people/<id>', methods=['GET'])
def people_id(id=''):
	data = {'ret': 0}
	people = People.objects(email=id).first() if is_valid_email(id) else People.objects(id=id).first()
	if people:
		data['ret'] = 1
		data['people'] = people.json()
	return jsonify(**data)


@app.route('/v1/people/<id>/activation', methods=['POST'])
def activate(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people and people.activation.code == request.args.get('code', default=''):
		if not people.activation.status:
			people.activation.time = datetime.datetime.now()
			people.activation.status = True
			people.save()
			app.logger.info('User {} activated'.format(people.id))
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/oauth2/tokens', methods=['POST'])
def sign_in():
	data = {'ret': 0}
	username = request.form['username']
	people = People.objects(email=username).first() if is_valid_email(username) else People.objects(id=username).first()
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
Resource needs access token
"""

def access_token_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		people = People.objects(id=kwargs['id']).first()
		authorization = request.headers.get('Authorization')
		if people and authorization:
			access_token = authorization.split(' ')[-1]
			if decrypt(access_token, people.activation.code).startswith(people.id + ' '):
				for token in people.tokens:
					if token.access_token == access_token:
						if datetime.datetime.now() > token.time + datetime.timedelta(seconds=token.expire_in):
							people.update(pull__tokens={'access_token':access_token})
						else:
							return f(*args, **kwargs)
		response = jsonify(ret=0)
		response.status_code = 401
		return response
	return decorated_function


def update_songs(ids):
	old_ids = [song.id for song in Song.objects(id__in=ids)]
	new_ids = [id for id in ids if id not in old_ids]
	data = get_songs(new_ids)
	if 'songs' in data and len(data['songs']) > 0:
		for json in data['songs']:
			song = Song()
			song.id = str(json['id'])
			song.name = json['name']
			song.source = json['mp3Url']
			song.img = json['album']['picUrl'] if 'album' in json else ''
			song.time = json['bMusic']['playTime'] if 'bMusic' in json else 0
			if 'artists' in json and len(json['artists']) > 0:
				song.artist.id = str(json['artists'][0]['id'])
				song.artist.name = json['artists'][0]['name']
			song.save()
			app.logger.info('Song {} was updated'.format(song.id))
	songs = Song.objects(id__in=ids)
	return sorted(songs, key=lambda k: ids.index(k.id))


@app.route('/v1/people/<id>/valid', methods=['GET'])
@access_token_required
def people_id_valid(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/people/<id>/detail', methods=['GET'])
@access_token_required
def people_id_detail(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		data['ret'] = 1
		data['people'] = people.detail()
	return jsonify(**data)


@app.route('/v1/people/<id>/player', methods=['GET', 'PUT'])
@access_token_required
def people_id_player(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		if request.method == 'PUT':
			people.player.update(set__status=request.form['status'])
			song = update_songs([request.form['sid'], ])[0]
			people.player.update(set__song=song)
		data['ret'] = 1
		data['player'] = People.objects(id=id).first().player.json()
	return jsonify(**data)


@app.route('/v1/people/<id>/player/playlist', methods=['POST', 'PUT', 'DELETE'])
@access_token_required
def people_id_player_playlist(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		if request.method == 'POST':
			song = update_songs([request.form['sid'], ])[0]
			if song not in people.player.playlist:
				people.player.update(push__playlist=song)
		elif request.method == 'PUT':
			sids = json.loads(request.form['sids'])
			people.player.update(set__playlist=update_songs(sids))
		elif request.method == 'DELETE':
			people.player.update(set__playlist=[])
		data['ret'] = 1
		data['player'] = People.objects(id=id).first().player.json()
	return jsonify(**data)


@app.route('/v1/people/<id>/player/playlist/<sid>', methods=['DELETE'])
@access_token_required
def people_id_player_playlist_sid(id='', sid=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		people.player.update(pull__playlist=sid)
		data['ret'] = 1
		data['player'] = People.objects(id=id).first().player.json()
	return jsonify(**data)


@app.route('/v1/people/<id>/requests', methods=['GET', 'POST', 'DELETE'])
@access_token_required
def requests_api(id=''):
	data = {'ret': 0}
	if request.method == 'GET':
		data['send'] = [req.json() for req in Request.objects(source=id)]
		data['receive'] = [req.json() for req in Request.objects(dest=id)]
		data['ret'] = 1
	elif request.method == 'POST':
		if id != request.form['id']:
			Request.objects(source=id, dest=request.form['id']).update_one(set__source=id, set__dest=request.form['id'], set__time=datetime.datetime.now(), upsert=True)
			data['ret'] = 1
	else:
		req = Request.objects(source=request.form['id'], dest=id).first()
		if req:
			req.delete()
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/people/<id>/connect/<cid>', methods=['GET'])
@access_token_required
def connect(id='', cid=''):
	data = {'ret': 0}
	req = Request.objects(source=cid, dest=id).first()
	if req:
		req.delete()
		req = Request.objects(source=id, dest=cid).first()
		if req:
			req.delete()
		master = People.objects(id=id).first()
		client = People.objects(id=cid).first()
		if master and client and master.id != client.id:
			def connected(master, client):
				return 'friend' in master and master.friend.id == client.id
			if not connected(master, client):
				if 'friend' in master:
					master.friend.update(unset__friend='')
					master.update(set__player=Player(master.player.status, master.player.song, master.player.playlist).save())
				if 'friend' in client:
					client.friend.update(unset__friend='')
				else:
					client.player.delete()
				master.update(set__friend=client.id)
				master = People.objects(id=id).first()
				client.update(set__friend=master.id)
				client.update(set__player=master.player)
				data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/people/<id>/disconnect', methods=['GET'])
@access_token_required
def disconnect(id=''):
	data = {'ret': 0}
	master = People.objects(id=id).first()
	if master and master.friend:
		master.friend.update(unset__friend='')
		master.update(unset__friend='')
		master.update(set__player=Player(master.player.status, master.player.song, master.player.playlist).save())
		data['ret'] = 1
	return jsonify(**data)


@app.route('/v1/people/<id>/sign-out', methods=['GET'])
@access_token_required
def sign_out(id=''):
	data = {'ret': 0}
	people = People.objects(id=id).first()
	if people:
		people.update(set__tokens=[])
		data['ret'] = 1
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


def is_valid_email(email):
	if not re.match("^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$", email):
		return False
	return True



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['SERVER']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

