#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pyaes
import base64
import codecs
import random
import string
import hashlib
import datetime
import configparser

from mongoengine import *

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

connect(db=config['DB']['NAME'], host=config['DB']['HOST'], port=int(config['DB']['PORT']))


"""
Utilities
"""

def random_str(length):
	return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


def sha(*params):
	h = hashlib.new(config['ENCRYPTION']['SHA'])
	h.update(' '.join(params).encode('utf-8'))
	return h.hexdigest()


def encrypt(plaintext, password):
	key = sha(password).encode('utf-8')[:32]
	aes = pyaes.AESModeOfOperationCTR(key)
	ciphertext = aes.encrypt(plaintext.encode('utf-8'))
	encoded = base64.b64encode(ciphertext)
	return encoded.decode('utf-8')


def decrypt(ciphertext, password):
	key = sha(password).encode('utf-8')[:32]
	aes = pyaes.AESModeOfOperationCTR(key)
	try:
		decoded = base64.b64decode(ciphertext.encode('utf-8'))
		plaintext = aes.decrypt(decoded)
		plaintext = plaintext.decode('utf-8')
	except:
		plaintext = ''
	return plaintext


"""
Musics
"""

class Artist(EmbeddedDocument):

	id = StringField(default='')
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
	artist = EmbeddedDocumentField('Artist', default=Artist())

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


"""
Player
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


"""
User
"""

class Activation(EmbeddedDocument):

	code = StringField(default=random_str(int(config['ACTIVATION']['CODE_LEN'])))
	time = DateTimeField(default=datetime.datetime.now())
	status = BooleanField(default=False)

	def json(self):
		json = {
			'time': self.time.strftime('%Y-%m-%d %H:%M:%S'),
			'status': self.status
		}
		return json


class Token(EmbeddedDocument):

	def new(id, code):
		return Token(access_token=encrypt('{} {}'.format(id, random_str(int(config['TOKEN']['LEN']))), code))

	access_token = StringField(default='')
	token_type = StringField(default=config['TOKEN']['TYPE'])
	expire_in = LongField(default=int(config['TOKEN']['EXPIRE_IN']))
	time = DateTimeField(default=datetime.datetime.now())

	def json(self):
		json ={
			'access_token': self.access_token,
			'token_type': self.token_type,
			'expire_in': self.expire_in
		}
		return json


class People(Document):

	def new(id, name, email, password):
		people = People(id=id, name=name, email=email, password=password, player=Player().save())
		people.password = sha(people.password, people.activation.code)
		return people

	id = StringField(primary_key=True)
	name = StringField(default='', required=True)
	email = StringField(default='', required=True, unique=True)
	password = StringField(default='', required=True)
	activation = EmbeddedDocumentField('Activation', default=Activation())
	tokens = ListField(EmbeddedDocumentField('Token'))
	player = ReferenceField('Player')
	friend = ReferenceField('People')

	def check_password(self, password):
		return self.password == sha(password, self.activation.code)

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


"""
Notification
"""

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

