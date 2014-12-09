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


app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_USERNAME'] = 'saberwork@qq.com'
app.config['MAIL_PASSWORD'] = 'Ball001'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

app.config['DOMAIN'] = 'localhost:5000'
app.config['BRAND'] = 'CodingHonor'
app.config['HOST'] = '0.0.0.0'
app.config['PORT'] = 5000

app.config['JSON_AS_ASCII'] = False
app.config['HEADERS'] = {'Referer': 'http://music.163.com'}
app.config['OFFSET'] = 0
app.config['LIMIT'] = 100


@app.route('/')
def root():
	# send('hello', '<a href="http://api.codinghonor.com/">test</a>', 'buaastorm@gmail.com')
	return redirect('/v1')


@app.route('/v1')
def index():
	# send_activation()
	return render_template('v1.html', version='v1', domain=app.config['DOMAIN'], brand=app.config['BRAND'], offset=app.config['OFFSET'], limit=app.config['LIMIT'])


@app.route('/v1/albums/<albumId>')
def album(albumId=''):
	url = 'http://music.163.com/album?id=%s' % albumId
	soup = BeautifulSoup(requests.get(url, headers=app.config['HEADERS']).text)
	data = {}
	data['id'] = albumId
	data['name'] = getText(soup.find('h2', class_='f-ff2'))
	data['artist'] = {}
	data['artist']['name'] = getText(soup.find('a', class_='s-fc7'))
	data['artist']['id'] = last('id=', soup.find('a', class_='s-fc7')['href'])
	intrNodes = soup.find_all('p', class_='intr')
	if len(intrNodes) >= 3:
		data['publishTime'] = last('：[ \n]*', getText(intrNodes[1]))
		data['company'] = last('：[ \n]*', getText(intrNodes[2]))
	data['songs'] = []
	for songNode in soup.find_all('tr', class_='ztag'):
		songDict = {}
		songDict['id'] = songNode['data-id']
		songDict['name'] = songNode.a['title']
		songDict['time'] = getText(songNode.find('td', 's-fc3'))
		data['songs'].append(songDict)
	return jsonify(**data)


@app.route('/v1/albums')
def albums():
	s, = parse_request('s')
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/search/get/web?csrf_token='
	payload = {'s': s, 'type': '10', 'offset': offset, 'total': 'true', 'limit': limit}
	r = requests.post(url, data=payload, headers=app.config['HEADERS'])
	return jsonify(**r.json())


@app.route('/v1/artists/<artistId>')
def artist(artistId=''):
	url = 'http://music.163.com/artist?id=%s' % artistId
	soup = BeautifulSoup(requests.get(url, headers=app.config['HEADERS']).text)
	data = {}
	data['id'] = artistId
	data['name'] = getText(soup.find('h2', id='artist-name'))
	data['songs'] = []
	for songNode in soup.find_all('tr', class_='ztag'):
		songDict = {}
		idNameNode = songNode.find('div', class_='ttc').a
		songDict['id'] = last('id=', idNameNode['href'] if idNameNode is not None else '')
		songDict['name'] = getText(idNameNode)
		songDict['time'] = getText(songNode.find('td', 's-fc3'))
		albumNode = songNode.find('td', class_='w4').a
		songDict['album'] = {}
		songDict['album']['id'] = last('id=', albumNode['href'] if albumNode is not None else '')
		songDict['album']['name'] = getText(albumNode)
		data['songs'].append(songDict)
	return jsonify(**data)


@app.route('/v1/artists')
def artists():
	s, = parse_request('s')
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/search/get/web?csrf_token='
	payload = {'s': s, 'type': '100', 'offset': offset, 'total': 'true', 'limit': limit}
	r = requests.post(url, data=payload, headers=app.config['HEADERS'])
	return jsonify(**r.json())


@app.route('/v1/new/albums/<area>')
def newAlbums(area='ALL'):
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/album/new?area=%s&offset=%d&total=true&limit=%d&csrf_token=' % (area, offset, limit)
	r = requests.get(url, headers=app.config['HEADERS'])
	return jsonify(**r.json())


@app.route('/v1/playlists/<playlistId>')
def playlist(playlistId=''):
	url = 'http://music.163.com/playlist?id=%s' % playlistId
	soup = BeautifulSoup(requests.get(url, headers=app.config['HEADERS']).text)
	data = {}
	data['id'] = playlistId
	data['name'] = getText(soup.find('h2', class_='f-ff2'))
	data['songs'] = []
	for songNode in soup.find_all('tr', class_='ztag'):
		songDict = {}
		tds = songNode.find_all('td')
		if len(tds) >= 5:
			idNameNode = tds[1].find('div', class_='ttc').a
			songDict['id'] = last('id=', idNameNode['href'] if idNameNode is not None else '')
			songDict['name'] = getText(idNameNode)
			songDict['time'] = getText(tds[2])
			artistNode = tds[3].a
			songDict['artist'] = {}
			songDict['artist']['id'] = last('id=', artistNode['href'] if artistNode is not None else '')
			songDict['artist']['name'] = getText(artistNode)
			albumaNode = tds[4].a
			songDict['album'] = {}
			songDict['album']['id'] = last('id=', albumaNode['href'] if albumaNode is not None else '')
			songDict['album']['name'] = getText(albumaNode)
			data['songs'].append(songDict)
	return jsonify(**data)


@app.route('/v1/playlists')
def playlists():
	s, = parse_request('s')
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/search/get/web?csrf_token='
	payload = {'s': s, 'type': '1000', 'offset': offset, 'total': 'true', 'limit': limit}
	r = requests.post(url, data=payload, headers=app.config['HEADERS'])
	return jsonify(**r.json())


@app.route('/v1/songs/<songId>')
def song(songId=''):
	url = 'http://music.163.com/song?id=%s' % songId
	soup = BeautifulSoup(requests.get(url, headers=app.config['HEADERS']).text)
	data = {}
	data['id'] = songId
	data['name'] = getText(soup.find('em', class_='f-ff2'))
	artistAlbumNodes = soup.find_all('a', class_='s-fc7')
	artistNode = artistAlbumNodes[0] if len(artistAlbumNodes) >= 1 else None
	data['artist'] = {}
	data['artist']['id'] = last('id=', artistNode['href'] if artistNode is not None else '')
	data['artist']['name'] = getText(artistNode)
	albumNode = artistAlbumNodes[1] if len(artistAlbumNodes) >= 2 else None
	data['album'] = {}
	data['album']['id'] = last('id=', albumNode['href'] if albumNode is not None else '')
	data['album']['name'] = getText(albumNode)
	data['lyrics'] = list(filter(bool, re.split('[\n]+', getText(soup.find('div', class_='bd-open')))))[:-1]
	return jsonify(**data)


@app.route('/v1/songs')
def songs():
	s, = parse_request('s')
	offset, limit = parse_offset_limit();
	url = 'http://music.163.com/api/search/get/web?csrf_token='
	payload = {'s': s, 'type': '1', 'offset': offset, 'total': 'true', 'limit': limit}
	r = requests.post(url, data=payload, headers=app.config['HEADERS'])
	return jsonify(**r.json())


@app.route('/v1/toplist')
def toplist():
	url = 'http://music.163.com/discover/toplist'
	soup = BeautifulSoup(requests.get(url, headers=app.config['HEADERS']).text)
	data = {}
	data['name'] = getText(soup.find('h2', class_='f-ff2'))
	data['songs'] = []
	for songNode in soup.find('table', class_='m-table').find_all('tr'):
		songDict = {}
		tds = songNode.find_all('td')
		if len(tds) >= 4:
			idNameNode = tds[1].find('div', class_='ttc').a
			songDict['id'] = last('id=', idNameNode['href'] if idNameNode is not None else '')
			songDict['name'] = getText(idNameNode)
			songDict['time'] = getText(tds[2])
			artistNode = tds[3].a
			songDict['artist'] = {}
			songDict['artist']['id'] = last('id=', artistNode['href'] if artistNode is not None else '')
			songDict['artist']['name'] = getText(artistNode)
			data['songs'].append(songDict)
	return jsonify(**data)


@app.route('/v1/user', methods=['POST'])
def user():
    pass


@app.route('/v1/users/<id>')
def users(id=''):
    pass


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
		ret[0] = app.config['OFFSET']
	try:
		ret[1] = int(ret[1])
	except ValueError:
		ret[1] = app.config['LIMIT']
	return ret


def getText(node):
	return node.get_text() if node is not None else ''


def last(sp, s):
	return re.split(sp, s if s is not None else '')[-1].strip()


def send_activation(html, recipient):
	msg = Message('%s Activation' % app.config['BRAND'], sender=(app.config['BRAND'], app.config['MAIL_USERNAME']))
	msg.html = html
	msg.add_recipient(recipient)
	mail.send(msg)



if __name__ == '__main__':
	app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)

