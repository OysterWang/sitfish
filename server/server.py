#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
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
Resource definition
"""

@app.route('/')
def host():
	return redirect('/v1')


@app.route('/v1')
def index():
	return render_template('v1.html', version='v1', host=config['SERVER']['HOST'], brand=config['DEFAULT']['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'])


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
	if t == '9':
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


"""
Account relevant
"""

@app.route('/v1/exist')
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
		user = User(uid=request.form['uid'], name=request.form['name'], email=request.form['email'], password=request.form['password'])
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


@app.route('/v1/activate/<uid>')
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
			data['uid'] = user.uid
			data['name'] = user.name
			data['access_token'] = user.access_token
	return jsonify(**data)


@app.route('/v1/validate', methods=['post'])
def validate():
	data = {'ret': 0}
	user = User.objects(uid=request.form['uid']).first()
	if user is not None:
		if user.access_token == request.form['access_token']:
			data['ret'] = 1
	return jsonify(**data)


# TYPE - 9
@app.route('/v1/users/<id>')
def users(id=''):
	user = User.objects(uid=id).first()
	data = user.json() if user is not None else {'code': '404'}
	return jsonify(**data)


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

