#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import string
import datetime

from mongoengine import *

ACTIVATION_CODE_LEN = 10

connect('vox')

class User(Document):

    email = StringField(primary_key=True)
    name = StringField(default='', required=True)
    her = StringField(default='')
    reg_time = DateTimeField(default=datetime.datetime.now())
    activation = BooleanField(default=False)
    activation_code = StringField(default=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(ACTIVATION_CODE_LEN)))
    access_token = StringField(default='')

    def __str__(self):
        return '<%s - %s>' % (self.email, self.name)

if __name__ == '__main__':
    for user in User.objects:
        print(user)
