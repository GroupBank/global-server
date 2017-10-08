import json

from collections import defaultdict
from django.test import TestCase
from django.urls import reverse

import common.crypto.ec_secp256k1 as crypto
from common.crypto import example_keys
from rest_app.models import Group, User, UOMe, UserDebt

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


class ConfirmUOMeTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user = User.objects.create(group=self.group, key=self.key)
        self.borrower = User.objects.create(group=self.group, key=example_keys.C2_pub)

    def test_confirm_first_uome(self):
        uome = UOMe.objects.create(group=self.group, lender=self.user,
                                   borrower=self.borrower,
                                   value=10,
                                   description='test')

        uome_payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'borrower': self.borrower.key,
                              'value': 10,
                              'description': 'test',
                              'uome_uuid': str(uome.uuid),
                              })
        uome_signature = crypto.sign(self.private_key, uome_payload)

        payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'uome_uuid': str(uome.uuid),
                              'user_signature': uome_signature,
                              })

        signature = crypto.sign(self.private_key, payload)
        response = self.client.post(reverse('rest:uome:confirm'),
                                    {'author': self.user.key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == self.user.key

        uome = UOMe.objects.get(pk=uome.uuid)
        assert uome.issuer_signature == uome_signature


class CancelUOMeTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user = User.objects.create(group=self.group, key=self.key)
        self.borrower = User.objects.create(group=self.group, key=example_keys.C2_pub)

    def test_cancel_unconfirmed_uome(self):
        uome = UOMe.objects.create(group=self.group, lender=self.user,
                                   borrower=self.borrower,
                                   value=10,
                                   description='test')

        issuer_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                     'issuer': self.user.key,
                                     'borrower': self.borrower.key,
                                     'value': 10,
                                     'description': 'test',
                                     'uome_uuid': str(uome.uuid),
                                     })

        issuer_signature = crypto.sign(self.private_key, issuer_payload)

        uome.issuer_signature = issuer_signature
        uome.save()

        payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'uome_uuid': str(uome.uuid),
                              })
        signature = crypto.sign(self.private_key, payload)

        response = self.client.post(reverse('rest:uome:cancel'),
                                    {'author': self.user.key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == self.user.key
        assert payload['uome_uuid'] == str(uome.uuid)

        assert UOMe.objects.filter(uuid=uome.uuid).first() is None

        # TODO: test for the other cases: uome doesn't exist, the user isn't the
        # issuer of the uome or the uome has already been confirmed


class GetPendingUOMesTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user = User.objects.create(group=self.group, key=self.key)
        self.other_user = User.objects.create(group=self.group, key=example_keys.C2_pub)

    def test_one_by_user_uome_and_one_for_user_uome(self):

        uome_by_user = UOMe.objects.create(group=self.group, lender=self.user,
                                           borrower=self.other_user, value=30,
                                           description="by user")

        uome_by_user_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                           'issuer': self.user.key,
                                           'borrower': self.other_user.key,
                                           'value': 30,
                                           'description': 'by user',
                                           'uome_uuid': str(uome_by_user.uuid),
                                           })
        uome_by_user_signature = crypto.sign(self.private_key, uome_by_user_payload)

        uome_by_user.issuer_signature = uome_by_user_signature
        uome_by_user.save()

        uome_for_user = UOMe.objects.create(group=self.group, lender=self.other_user,
                                            borrower=self.user, value=20,
                                            description="for user")

        uome_for_user_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                            'issuer': self.other_user.key,
                                            'borrower': self.user.key,
                                            'value': 20,
                                            'description': 'for user',
                                            'uome_uuid': str(uome_for_user.uuid),
                                            })
        uome_for_user_signature = crypto.sign(self.private_key, uome_for_user_payload)

        uome_for_user.issuer_signature = uome_for_user_signature
        uome_for_user.save()

        assert uome_by_user.borrower_signature == ''
        assert uome_by_user.issuer_signature != ''

        assert uome_for_user.borrower_signature == ''
        assert uome_for_user.issuer_signature != ''

        auth_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                   'user': self.user.key})
        auth_signature = crypto.sign(self.private_key, auth_payload)

        payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'user_signature': auth_signature})
        signature = crypto.sign(self.private_key, payload)

        response = self.client.post(reverse('rest:uome:get-pending'),
                                    {'author': self.user.key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == self.user.key

        issued_by_user = json.loads(payload['issued_by_user'])
        for uome in issued_by_user:
            assert uome['group_uuid'] == str(uome_by_user.group.uuid)
            assert uome['lender'] == uome_by_user.lender.key
            assert uome['borrower'] == uome_by_user.borrower.key
            assert uome['value'] == uome_by_user.value
            assert uome['description'] == uome_by_user.description
            assert uome['uuid'] == str(uome_by_user.uuid)
            assert uome['issuer_signature'] == uome_by_user_signature

        waiting_for_user = json.loads(payload['waiting_for_user'])
        for uome in waiting_for_user:
            assert uome['group_uuid'] == str(uome_by_user.group.uuid)
            assert uome['lender'] == uome_for_user.lender.key
            assert uome['borrower'] == uome_for_user.borrower.key
            assert uome['value'] == uome_for_user.value
            assert uome['description'] == uome_for_user.description
            assert uome['uuid'] == str(uome_for_user.uuid)
            assert uome['issuer_signature'] == uome_for_user_signature


class AcceptTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user = User.objects.create(group=self.group, key=self.key)
        self.lender = User.objects.create(group=self.group, key=example_keys.C2_pub)

    def test_confirm_first_uome(self):

        uome = UOMe.objects.create(group=self.group,
                                   lender=self.lender,
                                   borrower=self.user,
                                   value=10,
                                   description='test',
                                   )

        issuer_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                     'issuer': self.lender.key,
                                     'borrower': self.user.key,
                                     'value': 10,
                                     'description': 'test',
                                     'uome_uuid': str(uome.uuid),
                                     })
        issuer_signature = crypto.sign(example_keys.C2_priv, issuer_payload)

        uome.issuer_signature = issuer_signature
        uome.save()

        assert uome.borrower_signature == ''

        borrower_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                       'issuer': self.lender.key,
                                       'borrower': self.user.key,
                                       'value': 10,
                                       'description': 'test',
                                       'uome_uuid': str(uome.uuid),
                                       })
        borrower_signature = crypto.sign(self.private_key, borrower_payload)

        payload = json.dumps({'group_uuid': str(self.group.uuid),
                              'user': self.user.key,
                              'uome_uuid': str(uome.uuid),
                              'user_signature': borrower_signature,
                              })
        signature = crypto.sign(self.private_key, payload)

        response = self.client.post(reverse('rest:uome:accept'),
                                    {'author': self.user.key,
                                     'signature': signature,
                                     'payload': payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['group_uuid'] == str(self.group.uuid)
        assert payload['user'] == self.user.key

        uome = UOMe.objects.filter(group=self.group, uuid=uome.uuid).first()
        assert uome.borrower_signature == borrower_signature

        # Confirm totals
        totals = {}
        for user in User.objects.filter(group=self.group):
            totals[user] = user.balance

        assert totals == {self.user: -uome.value, self.lender: uome.value}

        # Confirm simplified debt
        simplified_debt = defaultdict(dict)
        for user_debt in UserDebt.objects.filter(group=self.group):
            simplified_debt[user_debt.borrower][user_debt.lender] = user_debt.value

        assert simplified_debt == {self.user: {self.lender: uome.value}}


class GetTotalsTests(TestCase):
    def setUp(self):
        self.private_key, self.key = example_keys.C1_priv, example_keys.C1_pub
        self.group = Group.objects.create(name='test', key=example_keys.G1_pub)
        self.user1 = User.objects.create(group=self.group, key=example_keys.C1_pub)
        self.user2 = User.objects.create(group=self.group, key=example_keys.C2_pub)
        self.user3 = User.objects.create(group=self.group, key=example_keys.C3_pub)

        self.user_payload = json.dumps({'group_uuid': str(self.group.uuid),
                                        'user': self.user1.key,
                                        })
        self.user_signature = crypto.sign(self.private_key, self.user_payload)

        self.payload = json.dumps({'group_uuid': str(self.group.uuid),
                                   'user': self.user1.key,
                                   'user_signature': self.user_signature,
                                   })
        self.signature = crypto.sign(self.private_key, self.payload)

    def test_get_totals_no_uome(self):
        response = self.client.post(reverse('rest:uome:get-totals'),
                                    {'author': self.key,
                                     'signature': self.signature,
                                     'payload': self.payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['user_balance'] == 0
        assert payload['suggested_transactions'] == {}

    def test_get_totals_one_unconfirmed_uome(self):
        UOMe.objects.create(group=self.group, lender=self.user2, borrower=self.user1,
                            value=10, description="test", issuer_signature='meh')

        response = self.client.post(reverse('rest:uome:get-totals'),
                                    {'author': self.key,
                                     'signature': self.signature,
                                     'payload': self.payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['user_balance'] == 0
        assert payload['suggested_transactions'] == {}

    def test_get_totals_one_confirmed_uome(self):
        uome = UserDebt.objects.create(group=self.group, lender=self.user2,
                                       borrower=self.user1, value=1000)

        self.user2.balance = +uome.value
        self.user2.save()
        self.user1.balance = -uome.value
        self.user1.save()

        response = self.client.post(reverse('rest:uome:get-totals'),
                                    {'author': self.key,
                                     'signature': self.signature,
                                     'payload': self.payload})

        assert response.status_code == 200
        assert response['author'] == server_key
        crypto.verify(server_key, response['signature'], response.content.decode())

        payload = json.loads(response.content.decode())

        assert payload['user_balance'] == -uome.value
        assert payload['suggested_transactions'] == {self.user2.key: uome.value}
