#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import render_template

from flask.ext.mail import Mail
from flask.ext.mail import Message

from bs4 import BeautifulSoup

from database import *


app = Flask(__name__)

app.config['DOMAIN_API'] = 'localhost:5000'
app.config['BRAND'] = 'Vox'
app.config['HOST'] = '0.0.0.0'
app.config['PORT'] = 5000

app.config['JSON_AS_ASCII'] = False

app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_USERNAME'] = 'saberwork@qq.com'
app.config['MAIL_PASSWORD'] = 'Ball001'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

app.config['HEADERS'] = {'Referer': 'http://music.163.com'}
app.config['OFFSET'] = 0
app.config['LIMIT'] = 100


"""
Resource definition
"""

@app.route('/')
def domain():
	return redirect('/v1')


@app.route('/v1')
def index():
	return render_template('v1.html', version='v1', domain=app.config['DOMAIN_API'], brand=app.config['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'])


@app.route('/v1/search')
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
	if t is '9':
		data = {'users': []}
		for user in User.objects(uid__contains=s).limit(limit):
			data['users'].append(user.json())
	else:
		url = 'http://music.163.com/api/search/pc'
		payload = {'s': s, 'type': t, 'offset': offset, 'total': 'true', 'limit': limit}
		data = requests.post(url, data=payload, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1
@app.route('/v1/songs/<id>')
def songs(id=''):
	url = 'http://music.163.com/api/song/detail?ids=[%s]' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 10
@app.route('/v1/albums/<id>')
def albums(id=''):
	url = 'http://music.163.com/api/album/%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 100
@app.route('/v1/artists/<id>')
def artists(id=''):
	url = 'http://music.163.com/api/artist/albums/%s?limit=%d' % (id, app.config['LIMIT'])
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1000
@app.route('/v1/playlists/<id>')
def playlists(id=''):
	url = 'http://music.163.com/api/playlist/detail?id=%s' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 1006
@app.route('/v1/lyrics/<id>')
def lyrics(id=''):
	url = 'http://music.163.com/api/song/lyric?id=%s&lv=-1&kv=-1&tv=-1' % id
	data = requests.get(url, headers=app.config['HEADERS']).json()
	return jsonify(**data)


# TYPE - 9
@app.route('/v1/users/<id>')
def users(id=''):
	user = User.objects(uid=id).first()
	data = user.json() if user is not None else {'code': '404'}
	return jsonify(**data)


@app.route('/v1/count')
def count():
	s = request.args.get('s', default='')
	t = request.args.get('t', default='0') # uid:0, email:1
	data = {}
	if t is '0':
		data['count'] = User.objects(uid=s).count()
	elif t is '1':
		data['count'] = User.objects(email=s).count()
	else:
		data['code'] = '404'
	return jsonify(**data)

"""
Email relevant
"""

def send_activation(html, recipient):
	msg = Message('%s Activation' % app.config['BRAND'], sender=(app.config['BRAND'], app.config['MAIL_USERNAME']))
	msg.html = html
	msg.add_recipient(recipient)
	mail.send(msg)



if __name__ == '__main__':
	app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)

