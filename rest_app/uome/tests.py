import json

from django.test import TestCase
from django.urls import reverse

import common.crypto.rsa as crypto
from common.crypto import example_keys
from rest_app.models import Group, User, UOMe

_, server_key = crypto.load_keys('server_keys.pem')

# Good rules-of-thumb include having:
#
# - a separate TestClass for each model or view
# - a separate test method for each set of conditions you want to test
# - test method names that describe their function
# TODO: check this out, looks cool: https://docs.djangoproject.com/en/1.10/ref/validators/


class IssueUOMeTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user = User.objects.create(group=self.group, key=self.key)
        self.borrower = User.objects.create(group=self.group, key=example_keys.C2_pub)

    def test_add_first_uome(self):

        auth_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                   'user': self.user.key})

        auth_signature = crypto.sign(self.private_key, auth_payload)

        payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'borrower': self.borrower.key,
                              'value': 1000,
                              'description': 'my description',
                              'user_signature': auth_signature})

        # todo: recheck if this is a security issue (might count as accepting the uome)
        signature = crypto.sign(self.private_key, payload)

        response = self.client.post(reverse('rest:uome:issue'),
                                    {'author': self.user.key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 201
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == self.user.key
        assert payload['borrower'] == self.borrower.key
        assert payload['value'] == 1000
        assert payload['description'] == 'my description'

        uome = UOMe.objects.get(pk=payload['uome_uuid'])
        assert uome.issuer_signature == ''
