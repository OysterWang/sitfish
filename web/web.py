#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
import requests
import configparser

from flask import Flask
from flask import jsonify
from flask import request
from flask import session
from flask import redirect
from flask import render_template

from pprint import pprint

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

base_params = {'domain': config['WEB']['HOST'], 'brand': config['DEFAULT']['BRAND']}

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['JSON_AS_ASCII'] = False


"""
Foundation
"""

@app.route('/')
def index():
	url = 'http://%s/v1/toplists/3778678' % config['SERVER']['HOST']
	data = requests.get(url).json()
	return pjax('toplist.html', id='3778678', songs=data['songs'])


@app.route('/toplist')
def toplist():
	id = request.args.get('id', default='3778678')
	url = 'http://%s/v1/toplists/%s' % (config['SERVER']['HOST'], id)
	data = requests.get(url).json()
	return pjax('toplist.html', id=id, songs=data['songs'])


@app.route('/playlist')
def playlist():
	return pjax('playlist.html')


@app.route('/albumnew')
def albumnew():
	return pjax('albumnew.html')


@app.route('/player', methods=['GET', 'POST'])
def player_songs():
	if request.method == 'GET':
		pass
	else:
		pass


"""
User management
"""

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
	if request.method == 'GET':
		return render_template('sign_up.html', **base_params)
	else:
		url = 'http://%s/v1/sign-up' % config['SERVER']['HOST']
		payload = {'uid': request.form['uid'], 'name': request.form['name'], 'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			return render_template('tips.html', tips='%s，恭喜，注册成功！我们已向%s发送了一封邮件，请尽快登录并激活当前账户。' % (payload['name'], payload['email']), **base_params)
		else:
			return render_template('tips.html', tips='%s，抱歉，注册失败，请稍候再次尝试。' % payload['name'], **base_params)


@app.route('/activate/<uid>')
def activate(uid=''):
	url = 'http://%s/v1/activate/%s?code=%s' % (config['SERVER']['HOST'], uid, request.args.get('code', default=''))
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
			session['uid'] = data['user']['uid']
			session['access_token'] = data['user']['access_token']
			return redirect('/')
		else:
			return render_template('sign_in.html', ret=data['ret'], email=payload['email'], password=payload['password'], **base_params)


@app.route('/sign-out')
def sign_out():
	session.clear()
	return redirect('/')


@app.route('/api/<path:path>', methods=['get', 'post'])
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
Utilities
"""

def pjax(template, **params):
	data = validate()
	if data is not None and data['ret'] == 1:
		params.update(data['user'])
		if 'X-PJAX' in request.headers:
			return render_template(template, **dict(base_params, **params))
		else:
			return render_template("base.html", template=template, **dict(base_params, **params))
	else:
		return render_template('index.html', **base_params)


def validate():
	if 'uid' in session and 'access_token' in session:
		url = 'http://%s/v1/validate' % config['SERVER']['HOST']
		payload = {'uid': session['uid'], 'access_token': session['access_token']}
		return requests.post(url, data=payload).json()
	return None



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

