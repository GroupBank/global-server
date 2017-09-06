from uuid import UUID, uuid4

from django.test import TestCase
from django.urls import reverse
from django.conf import settings

import json
import pytest

from common.crypto import example_keys
import common.crypto.rsa as crypto
from rest_app.models import Group, User

_, server_key = crypto.load_keys('server_keys.pem')

# Good rules-of-thumb include having:
#
# - a separate TestClass for each model or view
# - a separate test method for each set of conditions you want to test
# - test method names that describe their function
# TODO: check this out, looks cool: https://docs.djangoproject.com/en/1.10/ref/validators/


class RegisterGroupTests(TestCase):
    # TODO: add proxy/name server address?
    # TODO: Avoid testing the signature verification middleware. https://stackoverflow.com/questions/18025367/disable-a-specific-django-middleware-during-tests
    def test_correct_inputs(self):
        group_name = 'test_name'
        priv_key, pub_key = example_keys.G1_priv, example_keys.G1_pub
        id = pub_key

        payload = json.dumps({'group_name': group_name, 'group_key': pub_key})
        signature = crypto.sign(priv_key, payload)

        response = self.client.post(reverse('rest:group:register'),
                                            {'author': id,
                                             'signature': signature,
                                             'payload': payload})

        assert response.status_code == 201
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_name'] == group_name
        assert payload['group_key'] == pub_key
        UUID(payload['group_uuid'])

    def test_invalid_message(self):
        group_name = 'test_name'
        priv_key, pub_key = example_keys.G1_priv, example_keys.G1_pub

        payload = json.dumps({'group_name': group_name})  # missing 'group_key' field
        signature = crypto.sign(priv_key, payload)

        response = self.client.post(reverse('rest:group:register'),
                                    {'author': pub_key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 400
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

    def test_invalid_signature(self):
        group_name = 'test_name'
        priv_key, pub_key = example_keys.G1_priv, example_keys.G1_pub

        sent_payload = json.dumps({'group_name': group_name, 'group_key': pub_key})

        signed_payload = json.dumps({'group_name': group_name})  # missing 'group_key' field
        signature = crypto.sign(example_keys.G1_priv, signed_payload)

        response = self.client.post(reverse('rest:group:register'),
                                    {'author': id,
                                     'signature': signature,
                                     'payload': sent_payload})

        assert response.status_code == 403
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())


class RegisterUserTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)

    def test_new_user_to_existing_group(self):
        user_priv, user_pub = example_keys.C1_priv, example_keys.C1_pub
        group_priv, group_pub = example_keys.G1_priv, example_keys.G1_pub

        payload = json.dumps({'user_key': user_pub, 'group_uuid': str(self.group.uuid)})
        signature = crypto.sign(group_priv, payload)

        response = self.client.post(reverse('rest:group:register-user'),
                                        {'author': group_pub,
                                         'signature': signature,
                                         'payload': payload})

        assert response.status_code == 201
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == user_pub

    def test_new_user_invalid_group_uuid(self):
        user_priv, user_pub = example_keys.C1_priv, example_keys.C1_pub
        group_priv, group_pub = example_keys.G1_priv, example_keys.G1_pub

        payload = json.dumps({'user_key': user_pub, 'group_uuid': 'random_uuid'})
        signature = crypto.sign(group_priv, payload)

        response = self.client.post(reverse('rest:group:register-user'),
                                    {'author': group_pub,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 400

        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

    def test_new_user_non_existent_group(self):
        user_priv, user_pub = example_keys.C1_priv, example_keys.C1_pub
        group_priv, group_pub = example_keys.G2_priv, example_keys.G2_pub

        group_uuid = str(uuid4())

        payload = json.dumps({'user_key': user_pub, 'group_uuid': group_uuid})
        signature = crypto.sign(group_priv, payload)

        response = self.client.post(reverse('rest:group:register-user'),
                                    {'author': group_pub,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 400

        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

