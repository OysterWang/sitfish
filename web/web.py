#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask import session
from flask import redirect
from flask import render_template


app = Flask(__name__)

app.config['DOMAIN_API'] = 'localhost:5000'
app.config['DOMAIN_WEB'] = 'localhost:4000'
app.config['BRAND'] = 'Vox'
app.config['HOST'] = '0.0.0.0'
app.config['PORT'] = 4000


@app.route('/')
def index():
	if is_login():
		return render_template('index.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND'], name='寻找蝌蚪吗', avatar='')
	else:
		return render_template('cover.html', domain=app.config['DOMAIN_WEB'], brand=app.config['BRAND']);


def is_login():
	return False


if __name__ == '__main__':
	app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)

