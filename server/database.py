#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import random
import string
import hashlib
import datetime
import configparser

from mongoengine import *
import pprint

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

connect(db=config['DB']['NAME'], host=config['DB']['HOST'], port=int(config['DB']['PORT']))


"""
Utilities
"""

def random_str(length):
	return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def sha(*params):
	h = hashlib.new(config['SERVER']['SHA'])
	h.update(' '.join(params).encode('utf-8'))
	return h.hexdigest()


"""
Musics
"""

class Song(Document):

	id = StringField(primary_key=True)
	name = StringField(default='')
	source = StringField(default='')
	img = StringField(default='')
	time = LongField(default=0)
	artist = ReferenceField('Artist')

	def json(self):
		json = {
			'id': self.id,
			'name': self.name,
			'source': self.source,
			'img': self.img,
			'time': self.time,
			'artist': self.artist.json() if self.artist else {}
		}
		return json


class Artist(Document):

	id = StringField(primary_key=True)
	name = StringField(default='')

	def json(self):
		json = {
			'id': self.id,
			'name': self.name
		}
		return json


"""
User
"""

class Player(Document):

	status = StringField(default='stopped')
	song = ReferenceField('Song')
	playlist = ListField(ReferenceField('Song'))

	def json(self):
		json = {
			'status': self.status,
			'song': self.song.json() if self.song else {},
			'playlist': [s.json() for s in self.playlist]
		}
		return json


class People(Document):

	class Activation(EmbeddedDocument):

		code = StringField(default=random_str(int(config['SERVER']['ACT_CODE_LEN'])))
		time = DateTimeField(default=datetime.datetime.now())
		status = BooleanField(default=False)

		def json(self):
			json = {
				'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
				'status': self.status
			}
			return json

	class Token(EmbeddedDocument):

		access_token = StringField(default='')
		token_type = StringField(default='Bearer')
		expire_in = LongField(default=int(config['SERVER']['TOKEN_EXPIRE_IN']))
		time = DateTimeField(default=datetime.datetime.now())

		def json(self):
			json ={
				'access_token': self.access_token,
				'token_type': self.token_type,
				'expire_in': self.expire_in
			}
			return json

	id = StringField(primary_key=True)
	name = StringField(default='', required=True)
	email = StringField(default='', required=True, unique=True)
	password = StringField(default='', required=True)
	activation = EmbeddedDocumentField('Activation', default=Activation())
	friend = ReferenceField('People')
	player = ReferenceField('Player')

	def __init__(self, *args, **kwargs):
		Document.__init__(self, *args, **kwargs)
		self.password = sha(self.password)
		self.player = Player().save()

	def json(self):
		json = {
			'id': self.id,
			'name': self.name,
			'activation': self.activation.json()
		}
		return json

	def detail(self):
		json = {
			'id': self.id,
			'name': self.name,
			'email': self.email,
			'activation': self.activation.json(),
			'friend': {
				'id': self.friend.id if self.friend else '',
				'name': self.friend.name if self.friend else ''
			},
			'player': self.player.json()
		}
		return json


class Notification(Document):

	nfrom = StringField(required=True)
	nto = StringField(required=True)
	ntype = StringField(required=True)
	content = StringField(required=True)
	time = DateTimeField(default=datetime.datetime.now())
	read = BooleanField(default=False)

	def json(self):
		json = {
			'from': self.nfrom,
			'to': self.nto,
			'type': self.ntype,
			'content': self.content,
			'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
			'read': self.read
		}
		return json



if __name__ == '__main__':
	# p = People(id='zhaolong', name='赵龙', email='hello@gmail.com', password='hello001').save()
	# pprint(p.detail())
	d = {
		'name':'zhaolong',
		'address': {'a':'b', 'c':'d'}
	}
	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(d)

