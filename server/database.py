#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import random
import string
import datetime
import configparser

from mongoengine import *
from pprint import pprint

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

connect(db=config['DB']['NAME'], host=config['DB']['HOST'], port=int(config['DB']['PORT']))


class Artist(Document):

	id = StringField(primary_key=True)
	name = StringField(default='')

	def json(self):
		json = {
			'id': self.id,
			'name': self.name
		}
		return json


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
			'artist': self.artist.json()
		}
		return json


class Player(Document):

	status = StringField(default='stopped')
	song = ReferenceField('Song')
	playlist = ListField(ReferenceField('Song'))

	def json(self):
		json = {
			'status': self.status,
			'song': self.song.json(),
			'playlist': [s.json() for s in self.playlist]
		}
		return json


class People(Document):

	class Activation(EmbeddedDocument):

		code = StringField(default=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(int(config['DB']['ACT_CODE_LEN']))))
		time = DateTimeField(default=datetime.datetime.now())
		status = BooleanField(default=False)

		def json(self):
			json = {
				'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
				'status': self.status
			}
			return json

	class Token(EmbeddedDocument):

		value = StringField(default='')
		expire = DateTimeField(default=datetime.datetime.now()+datetime.timedelta(days=int(config['DEFAULT']['TOKEN_EXPIRE'])))

		def json(self):
			json ={
				'value': self.value,
				'expire': self.expire.strftime('%Y-%m-%d %H:%M:%S')
			}
			return json

	id = StringField(primary_key=True)
	name = StringField(default='', required=True)
	email = StringField(default='', required=True, unique=True)
	password = StringField(default='', required=True)
	activation = EmbeddedDocumentField('Activation', default=Activation())
	tokens = ListField(EmbeddedDocumentField('Token'))
	friend = ReferenceField('People')
	player = ReferenceField('Player')

	def create(id='', name='', email='', password=''):
		player = Player()
		player.save()
		people = People(id=id, name=name, email=email, password=password, player=player)
		return people

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
				'id': self.friend.id if self.friend is not None else '',
				'name': self.friend.name if self.friend is not None else ''
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
	pass

