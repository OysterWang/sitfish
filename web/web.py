#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import codecs
import requests
import configparser

from flask import Flask
from flask import jsonify
from flask import request
from flask import session
from flask import redirect
from flask import render_template

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

params = {'domain': config['WEB']['HOST'], 'brand': config['DEFAULT']['BRAND']}

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route('/')
def index():
	if validate():
		return render_template('index.html', uid=session['uid'], name=session['name'], **params)
	else:
		return render_template('sign_out.html', **params)


@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
	if request.method == 'GET':
		return render_template('sign_up.html', **params)
	else:
		url = 'http://%s/v1/sign-up' % config['SERVER']['HOST']
		payload = {'uid': request.form['uid'], 'name': request.form['name'], 'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['ret'] == 1:
			return render_template('tips.html', tips='%s，恭喜，注册成功！我们已向%s发送了一封邮件，请尽快登录并激活当前账户。' % (payload['name'], payload['email']), **params)
		else:
			return render_template('tips.html', tips='%s，抱歉，注册失败，请稍候再次尝试。' % payload['name'], **params)


@app.route('/activate/<uid>')
def activate(uid=''):
	url = 'http://%s/v1/activate/%s?code=%s' % (config['SERVER']['HOST'], uid, request.args.get('code', default=''))
	data = requests.get(url).json()
	print(data)
	if data['ret'] == 1:
		return render_template('tips.html', tips='激活成功！', **params)
	else:
		return render_template('tips.html', tips='激活失败……', **params)


@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
	if request.method == 'GET':
		return render_template('sign_in.html', error=False, email='', password='', **params)
	else:
		url = 'http://%s/v1/sign-in' % config['SERVER']['HOST']
		payload = {'email': request.form['email'], 'password': request.form['password']}
		data = requests.post(url, data=payload).json()
		if data['access_token'] == '':
			return render_template('sign_in.html', error=True, email=payload['email'], password=payload['password'], **params)
		else:
			session['uid'] = data['uid']
			session['name'] = data['name']
			session['access_token'] = data['access_token']
			return redirect('/')


@app.route('/sign-out')
def sign_out():
	session.clear()
	return redirect('/')


@app.route('/api/<path:path>')
def api(path=''):
	url = 'http://%s/%s?%s' % (config['SERVER']['HOST'], path, '&'.join(['%s=%s' % (key, request.args[key]) for key in request.args]))
	data = requests.get(url).json()
	return jsonify(**data)


def validate():
	if 'uid' in session and 'access_token' in session:
		url = 'http://%s/v1/validate' % config['SERVER']['HOST']
		payload = {'uid': session['uid'], 'access_token': session['access_token']}
		data = requests.post(url, data=payload).json()
		return data['ret'] == 1
	return False


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

