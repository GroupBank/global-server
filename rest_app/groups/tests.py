from uuid import UUID

from django.test import TestCase
from django.urls import reverse
from django.conf import settings

import json
import pytest

from common.crypto import example_keys
from common.crypto.rsa import sign, verify

# Good rules-of-thumb include having:
#
# - a separate TestClass for each model or view
# - a separate test method for each set of conditions you want to test
# - test method names that describe their function
# TODO: check this out, looks cool: https://docs.djangoproject.com/en/1.10/ref/validators/


class RegisterGroupTests(TestCase):
    # TODO: add proxy/name server address?
    # TODO: Avoid testing the signature verification middleware. https://stackoverflow.com/questions/18025367/disable-a-specific-django-middleware-during-tests
    def test_correct_inputs_no_signing(self):
        group_name = 'test_name'
        priv_key, pub_key = example_keys.G1_priv, example_keys.G1_pub
        id = pub_key

        payload = json.dumps({'group_name': group_name, 'group_key': pub_key})
        signature = sign(priv_key, payload)

        raw_response = self.client.post(reverse('rest:group:register'),
                                        {'author': id,
                                         'signature': signature,
                                         'payload': payload,
                                         })

        assert raw_response.status_code == 201

        response = json.loads(raw_response.content.decode())

        assert response['group_name'] == group_name
        assert response['group_key'] == pub_key
        UUID(response['group_uuid'])
