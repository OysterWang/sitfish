#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import render_template

from bs4 import BeautifulSoup


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

BRAND = 'CodingHonor'
DOMAIN = 'localhost'
HOST = '0.0.0.0'
PORT = 5000

OFFSET = 0
LIMIT = 100

HEADERS = {'Referer': 'http://music.163.com'}


@app.route('/')
def root():
	return redirect('/v1')


@app.route('/v1')
def index():
	return render_template('api_v1.html', version='v1', domain=DOMAIN, brand=BRAND, offset=OFFSET, limit=LIMIT)


@app.route('/v1/albums/<albumId>')
def album(albumId=''):
	url = 'http://music.163.com/album?id=%s' % albumId
	soup = BeautifulSoup(requests.get(url, headers=HEADERS).text)
	data = {}
	data['id'] = albumId
	data['name'] = soup.find('h2', class_='f-ff2').get_text()
	data['artist'] = {}
	data['artist']['name'] = soup.find('a', class_='s-fc7').get_text()
	last = lambda s, sp: re.split(sp, s if s is not None else '')[-1].strip()
	data['artist']['id'] = last(soup.find('a', class_='s-fc7')['href'], 'id=')
	intrs = soup.find_all('p', class_='intr')
	if (len(intrs) >= 3):
		data['publishTime'] = last(intrs[1].get_text(), '：[ \n]*')
		data['company'] = last(intrs[2].get_text(), '：[ \n]*')
	data['songs'] = []
	songs = soup.find_all('tr', class_='ztag')
	for song in songs:
		d = {}
		d['id'] = song['data-id']
		d['name'] = song.a['title']
		d['time'] = song.find('td', 's-fc3').get_text()
		data['songs'].append(d)
	return jsonify(**data)


@app.route('/v1/albums')
def albums():
	s, = parse_request('s')
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/search/get'
	payload = {'s': s, 'type': '10', 'offset': offset, 'total': 'true', 'limit': limit}
	r = requests.post(url, data=payload, headers=HEADERS)
	return jsonify(**r.json())


@app.route('/v1/new/albums/<area>')
def newAlbums(area='ALL'):
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/album/new?area=%s&offset=%d&total=true&limit=%d&csrf_token=' % (area, offset, limit)
	r = requests.get(url, headers=HEADERS)
	return jsonify(**r.json())


def parse_request(*params):
	ret = []
	for p in params:
		v = request.args.get(p)
		ret.append(v if v is not None else '')
	return ret


def parse_offset_limit(*params):
	ret = parse_request('offset', 'limit')
	try:
		ret[0] = int(ret[0])
	except ValueError:
		ret[0] = OFFSET
	try:
		ret[1] = int(ret[1])
	except ValueError:
		ret[1] = LIMIT
	return ret


if __name__ == '__main__':
	app.run(host=HOST, port=PORT, debug=True)
