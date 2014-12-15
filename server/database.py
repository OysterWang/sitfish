#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import codecs
import random
import string
import datetime
import configparser

from mongoengine import *

config = configparser.ConfigParser()
config.readfp(codecs.open("../config/config.ini", "r", "utf-8"))

connect(db=config['DB']['NAME'], host=config['DB']['HOST'], port=int(config['DB']['PORT']))


class User(Document):

    uid = StringField(primary_key=True)
    name = StringField(default='', required=True)
    email = StringField(default='', required=True, unique=True)
    password = StringField(default='', required=True)
    her = StringField(default='')
    reg_time = DateTimeField(default=datetime.datetime.now())
    activation = BooleanField(default=False)
    activation_code = StringField(default=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(int(config['DB']['ACT_CODE_LEN']))))
    access_token = StringField(default='')

    def __str__(self):
        return '<%s, %s, %s>' % (self.uid, self.name, self.email)

    def json(self):
        return {'uid': self.uid, 'name': self.name, 'email': self.email, 'her': self.her}


class Message(Document):

    source = StringField(required=True)
    dest = StringField(required=True)
    content = StringField(required=True)
    time = datetime.datetime.now()
    read = BooleanField(default=False)



if __name__ == '__main__':
    # Message(source='chenxiaohui', dest='chenjinnan', content='洛阳的项目做完了吗？').save()
    User(uid='zhaolong', name='赵龙', email='zhaolong@gmail.com', password='helloagain').save(force_insert=True)
    for u in User.objects():
        print(u)

