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
    def test_correct_inputs_no_signing(self):
        group_name = 'test_name'
        key = example_keys.G1_pub
        id = key

        payload = {'group_name': group_name, 'group_key': key}

        raw_response = self.client.post(reverse('group-servers:register-group'),
                                        {'author': id, 'data': json.dumps(payload)})

        assert raw_response.status_code == 201

        response = json.loads(raw_response.content.decode())

        assert response['group_name'] == group_name
        assert response['group_key'] == key
        UUID(response['group_uuid'])
