#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import requests
import configparser

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import render_template

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

params = {'domain': config['WEB']['HOST'], 'brand': config['DEFAULT']['BRAND']}

app = Flask(__name__)


@app.route('/')
def index():
	if is_login():
		return render_template('index.html', name='寻找蝌蚪吗', avatar='', **params)
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


@app.route('/sign-in')
def sign_in():
	return render_template('sign_in.html', **params)


@app.route('/api/<path:path>')
def api(path=''):
	url = 'http://%s/%s?%s' % (config['SERVER']['HOST'], path, '&'.join(['%s=%s' % (key, request.args[key]) for key in request.args]))
	data = requests.get(url).json()
	return jsonify(**data)


def is_login():
	return False



if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(config['WEB']['PORT']), debug=config['DEFAULT']['DEBUG'] == 'True')

