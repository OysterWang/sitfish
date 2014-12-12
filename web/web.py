#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import render_template


app = Flask(__name__)

app.config['DOMAIN_API'] = 'localhost:5000'
app.config['DOMAIN_WEB'] = 'localhost:4000'
app.config['BRAND'] = 'V.O.X'
app.config['HOST'] = '0.0.0.0'
app.config['PORT'] = 4000


@app.route('/')
def index():
	if is_login():
		return render_template('index.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND'], name='寻找蝌蚪吗', avatar='')
	else:
		return render_template('sign_out.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND'])


@app.route('/sign-in')
def sign_in():
	return render_template('sign_in.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND'])


@app.route('/sign-up')
def sign_up():
	return render_template('sign_up.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND'])


def catch_all(path):
    return 'You want path: %s' % path


@app.route('/api/<path:path>')
def api(path=''):
	url = 'http://%s/%s?%s' % (app.config['DOMAIN_API'], path, '&'.join(['%s=%s' % (key, request.args[key]) for key in request.args]))
	data = requests.get(url).json()
	return jsonify(**data)


def is_login():
	return False


if __name__ == '__main__':
	app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)

