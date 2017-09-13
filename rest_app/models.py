from django.db import models
import uuid

from common.crypto import rsa as crypto

UOME_DESCRIPTION_MAX_LENGTH = 1024


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


class UOMe(models.Model):
    class Meta:
        verbose_name_plural = "UOMe's"  # for the Django Admin panel

    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    borrower = models.ForeignKey(User, on_delete=models.PROTECT,
                                 related_name='uome_borrower')
    lender = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uome_lender')

    # In cents!
    value = models.PositiveIntegerField()

    description = models.CharField(max_length=UOME_DESCRIPTION_MAX_LENGTH)
    issuing_date = models.DateField('date issued', auto_now_add=True)

    # TODO: add blank=False all over the place?
    issuer_signature = models.CharField(max_length=crypto.SIGNATURE_LENGTH, default='',
                                        blank=True)
    borrower_signature = models.CharField(max_length=crypto.SIGNATURE_LENGTH, default='',
                                          blank=True)

    def __str__(self):
        return "%.3f€ from %s to %s: %s" % (
        int(self.value) / 100, self.borrower, self.lender, self.description)

    def to_dict_unconfirmed(self) -> dict:
        """
        Returns a dictionary of the relevant information of the UOMe without
         the borrower signature
        :return tuple:
        """
        return {'group_uuid': str(self.group.uuid),
                'lender': self.lender.key,
                'borrower': self.borrower.key,
                'value': self.value,
                'description': self.description,
                'uuid': str(self.uuid),
                'issuer_signature': self.issuer_signature,
                }


class UserDebt(models.Model):
    # the debt between users after simplification
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    borrower = models.ForeignKey(User, on_delete=models.PROTECT, related_name='debt_borrower')
    lender = models.ForeignKey(User, on_delete=models.PROTECT, related_name='debt_lender')

    value = models.PositiveIntegerField()  # In cents!

    def __str__(self):
        return "%.3f€ from %s to %s" % (int(self.value)/100, self.borrower, self.lender)
