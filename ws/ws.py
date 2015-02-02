#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../database')
from database import *
from mongoengine.errors import *

import json
import codecs
import datetime
import configparser

from autobahn.asyncio.websocket import WebSocketServerFactory
from autobahn.asyncio.websocket import WebSocketServerProtocol

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))


"""
Messgae Type:
 - player_sync
 - player_toggle
 - friend_request
"""


clients = {}

class PostmanProtocol(WebSocketServerProtocol):

	cid = ''

	def onConnect(self, request):
		log("client connecting: {}".format(request.peer))

	def onOpen(self):
		log("websocket connection open")

	def onMessage(self, payload, isBinary):
		if isBinary:
			log("binary message received: {} bytes".format(len(payload)))
		else:
			msg = payload.decode('utf-8')
			log("text message received: {}".format(msg))
			try:
				msg = json.loads(msg)
				if msg['from'] not in clients:
					self.cid = msg['from']
					clients[self.cid] = self
					log("{} connected".format(self.cid))
				if msg['type'] in ('player_sync', 'player_toggle'):
					sendMessage(msg['from'], payload, isBinary)
				elif msg['type'] in ('friend_request', ):
					sendTo(msg['from'], msg['to'], payload, isBinary)
			except:
				pass

	def onClose(self, wasClean, code, reason):
		clients.pop(self.cid)
		log("websocket connection {} closed: {}".format(self.cid, reason))


def sendMessage(source, payload, isBinary):
	people = People.objects(id=source).first()
	if people and 'friend' in people and people.friend.id in clients:
		clients[people.friend.id].sendMessage(payload, isBinary)
		log('sendMessage from {}: {}'.format(source, payload))
	else:
		log('sendMessage from {} failed'.format(source))


def sendTo(source, dest, payload, isBinary):
	if dest in clients:
		clients[dest].sendMessage(payload, isBinary)
		log('sendTo {}->{}: {}'.format(source, dest, payload))
	else:
		log('sendTo {}->{} failed'.format(source, dest))


def log(message):
	print('[{}] {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))



if __name__ == '__main__':

	try:
		import asyncio
	except ImportError:
		import trollius as asyncio

	host='0.0.0.0'
	port=int(config['WS']['PORT'])
	factory = WebSocketServerFactory("ws://{}:{}".format(host, port), debug=False)
	factory.protocol = PostmanProtocol

	loop = asyncio.get_event_loop()
	coro = loop.create_server(factory, host, port)
	server = loop.run_until_complete(coro)

	try:
		log('start work on ws://{}:{}'.format(host, port))
		loop.run_forever()
	except KeyboardInterrupt:
		pass
	finally:
		server.close()
		loop.close()

