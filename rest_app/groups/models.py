from django.db import models
import uuid

from common.crypto import rsa as crypto


class Group(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)

    key = models.CharField(max_length=crypto.B64_KEY_LENGTH)
    # owner_email = models.EmailField(max_length=254)
    # TODO: add proxy/name server address
