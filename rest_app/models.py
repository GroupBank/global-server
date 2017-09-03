from django.db import models
import uuid

from common.crypto import rsa as crypto


class Group(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)

    key = models.CharField(max_length=crypto.B64_KEY_LENGTH)
    # owner_email = models.EmailField(max_length=254)
    # TODO: add proxy/name server address
    # TODO: add currency type


class User(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    # the uuid is the signing key of the user!
    key = models.CharField(primary_key=True, max_length=crypto.B64_KEY_LENGTH)

    # if the user, after simplification, is a borrower
    balance = models.IntegerField(default=0)

    def __str__(self):
        return self.key
