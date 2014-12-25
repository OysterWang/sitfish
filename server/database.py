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


class Song(EmbeddedDocument):

	sid = StringField(default='')
	name = StringField(default='')
	source = StringField(default='')
	img = StringField(default='')
	time = LongField(default=0)
	artist_id = StringField(default='')
	artist_name = StringField(default='')

	def json(self):
		json = {
			'sid': self.sid,
			'name': self.name,
			'source': self.source,
			'img': self.img,
			'time': self.time,
			'artist_id': self.artist_id,
			'artist_name': self.artist_name
		}
		return json


class Player(Document):

	playing = BooleanField(default=False)
	current = EmbeddedDocumentField('Song', default=Song())
	playlist = ListField(EmbeddedDocumentField('Song'))

	def json(self):
		json = {
			'playing': self.playing,
			'current': self.current.json(),
			'playlist': [song.json() for song in self.playlist]
		}
		return json


class People(Document):

	pid = StringField(default='', required=True, unique=True)
	name = StringField(default='', required=True)
	email = StringField(default='', required=True, unique=True)
	password = StringField(default='', required=True)
	reg_time = DateTimeField(default=datetime.datetime.now())
	activation = BooleanField(default=False)
	activation_code = StringField(default=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(int(config['DB']['ACT_CODE_LEN']))))
	access_token = StringField(default='')
	friend = ReferenceField('People')
	player = ReferenceField('Player')

	def create(pid='', name='', email='', password=''):
		player = Player()
		player.save()
		people = People(pid=pid, name=name, email=email, password=password, player=player)
		return people

	def public_json(self):
		json = {
			'pid': self.pid,
			'name': self.name,
			'reg_time': self.reg_time.strftime('%Y-%m-%d %H:%M:%S')
		}
		return json

	def private_json(self):
		json = {
			'pid': self.pid,
			'name': self.name,
			'email': self.email,
			'reg_time': self.reg_time.strftime('%Y-%m-%d %H:%M:%S'),
			'access_token': self.access_token,
			'friend_id': self.friend.id if self.friend is not None else '',
			'friend_name': self.friend.name if self.friend is not None else '',
			'player': self.player.json()
		}
		return json


class Message(Document):

	source = StringField(required=True)
	dest = StringField(required=True)
	content = StringField(required=True)
	time = datetime.datetime.now()
	read = BooleanField(default=False)



if __name__ == '__main__':
	pass

