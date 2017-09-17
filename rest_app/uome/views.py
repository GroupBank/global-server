import json
import logging

from collections import defaultdict
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST

from common.crypto import rsa as crypto
from common.decorators import verify_author
from rest_app.models import Group, User, UOMe, UOME_DESCRIPTION_MAX_LENGTH, UserDebt
from rest_app.utils import simplify_debt

logger = logging.getLogger(__name__)


@verify_author
@require_POST
def issue(request):
    """
    Used by a user to issue an unconfirmed UOMe to another user
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        borrower_id = payload['borrower']
        value = payload['value']
        description = payload['description']
        auth_signature = payload['user_signature']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if request.POST['author'] != user_id:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    auth_payload = json.dumps({'group_uuid': str(group_uuid), 'user': user_id})

    try:
        crypto.verify(user_id, auth_signature, auth_payload)
    except (crypto.InvalidKey, crypto.InvalidSignature):
        logger.info('Request with invalid signature or key by author %s' % user_id)
        return HttpResponseForbidden()

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
        borrower = User.objects.get(group=group, key=borrower_id)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if key is not valid
        logger.info('Request tried to issue uome for non-existent group %s'
                    ', user %s or borrower %s' % (group_uuid, user_id, borrower_id))
        return HttpResponseBadRequest()

    if value <= 0:  # So it's not possible to invert the direction of the UOMe
        logger.info('Request tried to issue a uome with negative value (user %s)', user)
        return HttpResponseBadRequest()

    if len(description) > UOME_DESCRIPTION_MAX_LENGTH:
        logger.info('Request tried to issue a uome with invalid description (user %s)',user)
        return HttpResponseBadRequest()

    if user == borrower:  # That would just be weird...
        logger.info('Request tried to issue a uome from a user (%s) to themselves', user)
        return HttpResponseBadRequest()

    # TODO: the description can leak information, maybe it should be encrypted
    uome = UOMe.objects.create(group=group, lender=user, borrower=borrower, value=value,
                               description=description)

    response = json.dumps({'group_uuid': str(group.uuid),
                           'user': user.key,
                           'borrower': borrower.key,
                           'value': value,
                           'description': description,
                           'uome_uuid': str(uome.uuid)})

    logger.info('New uome %s issued in group %s by user %s' % (uome.uuid, group_uuid, user_id))
    return HttpResponse(response, status=201)


@verify_author
@require_POST
def confirm(request):
    """
    Used by a user to confirm an unconfirmed UOMe after the server assigns it an uuid
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        uome_uuid = payload['uome_uuid']
        user_signature = payload['user_signature']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if request.POST['author'] != user_id:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
        uome = UOMe.objects.get(pk=uome_uuid)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if key not valid
        logger.info('Request tried to confirm uome %s for non-existent group %s'
                    ', user %s' % (uome_uuid, group_uuid, user_id))
        return HttpResponseBadRequest()

    uome_payload = json.dumps({
        'group_uuid': str(uome.group.uuid),
        'user': uome.lender.key,
        'borrower': uome.borrower.key,
        'value': uome.value,
        'description': uome.description,
        'uome_uuid': str(uome.uuid),
    })

    try:
        crypto.verify(user_id, user_signature, uome_payload)
    except (crypto.InvalidKey, crypto.InvalidSignature):
        logger.info('Request with invalid signature or key by author %s' % user_id)
        return HttpResponseForbidden()

    # TODO: the description can leak information, maybe it should be encrypted
    uome.issuer_signature = payload['user_signature']
    uome.save()

    # user created, create the response object
    response = json.dumps({'group_uuid': str(group.uuid), 'user': user.key})

    logger.info('New uome %s confirmed in group %s by user %s' % (uome.uuid, group_uuid, user_id))
    return HttpResponse(response, status=200)


@verify_author
@require_POST
def cancel(request):
    """
    Used by a user to cancel a UOMe that has not yet been accepted by the borrower
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        uome_uuid = payload['uome_uuid']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if request.POST['author'] != user_id:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
        uome = UOMe.objects.get(group=group, uuid=uome_uuid)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if the key is invalid
        logger.info('Request tried to cancel uome %s for non-existent group %s'
                    ', user %s' % (uome_uuid, group_uuid, user_id))
        return HttpResponseBadRequest()

    if user.key == uome.lender.key and uome.borrower_signature == '':

        response = json.dumps({'group_uuid': str(group.uuid),
                               'user': user.key,
                               'uome_uuid': str(uome.uuid),
                               })

        uome.delete()

        logger.info('UOMe %s was deleted' % uome_uuid)
        return HttpResponse(response, status=200)
    else:
        return HttpResponseForbidden()


@verify_author
@require_POST
def get_pending(request):
    """
    Used by a user to request a list of pending (not yet accepted) UOMes issued to/by them
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        auth_signature = payload['user_signature']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if request.POST['author'] != user_id:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if the key is invalid
        logger.info('Request tried accessing pending uomes for non-existent group %s'
                    ', user %s' % (group_uuid, user_id))
        return HttpResponseBadRequest()

    auth_payload = json.dumps({'group_uuid': str(group.uuid),
                               'user': user.key,
                               })

    try:  # verify the signatures
        crypto.verify(user.key, auth_signature, auth_payload)
    except (crypto.InvalidKey, crypto.InvalidSignature):
        logger.info('Request with invalid signature or key by author %s' % user_id)
        return HttpResponseForbidden()

    # TODO: add a test for uome's without issuer signatures
    uomes_by_user = UOMe.objects.filter(group=group, borrower_signature='',
                                        lender=user).exclude(issuer_signature='')
    uomes_for_user = UOMe.objects.filter(group=group, borrower_signature='',
                                         borrower=user).exclude(issuer_signature='')
    issued_by_user = []
    for uome in uomes_by_user:
        issued_by_user.append(uome.to_dict_unconfirmed())
    waiting_for_user = []
    for uome in uomes_for_user:
        waiting_for_user.append(uome.to_dict_unconfirmed())

    response = json.dumps({'group_uuid': str(group.uuid),
                           'user': user.key,
                           'issued_by_user': json.dumps(issued_by_user),
                           'waiting_for_user': json.dumps(waiting_for_user),
                           })

    logger.info('Sent pending uome list to user %s' % user_id)
    return HttpResponse(response, status=200)


# TODO: Think about data races a lot more
@transaction.atomic
@verify_author
@require_POST
def accept(request):
    """
       Used by a user to accept a pending UOMe issued to them
       """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        uome_uuid = payload['uome_uuid']
        uome_signature = payload['user_signature']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
        uome = UOMe.objects.get(group=group, uuid=uome_uuid)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if the key is invalid
        logger.info('Request tried accepting a uomes for non-existent group %s'
                    ', user %s or uome %s' % (group_uuid, user_id, uome_uuid))
        return HttpResponseBadRequest()

    if request.POST['author'] != user_id or request.POST['author'] != uome.borrower.key:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    uome_payload = json.dumps({'group_uuid': str(uome.group.uuid),
                               'issuer': uome.lender.key,
                               'borrower': uome.borrower.key,
                               'value': uome.value,
                               'description': uome.description,
                               'uome_uuid': str(uome.uuid),
                               })

    try:  # verify the signatures
        crypto.verify(user.key, uome_signature, uome_payload)
    except (crypto.InvalidKey, crypto.InvalidSignature):
        logger.info('Request with invalid signature or key by author %s' % user_id)
        return HttpResponseForbidden()

    uome.borrower_signature = uome_signature
    uome.save()

    # update the balances and suggestions of users
    group_users = User.objects.filter(group=group)

    totals = defaultdict(int)
    for group_user in group_users:
        totals[group_user.key] = group_user.balance

    new_uome = [uome.borrower.key, uome.lender.key, uome.value]
    new_totals, new_simplified_debt = simplify_debt.update_total_debt(totals, [new_uome])

    for group_user in group_users:
        group_user.balance = new_totals[group_user.key]
        group_user.save()

    # drop the previous user debt for this group, since it's now useless
    UserDebt.objects.filter(group=group).delete()

    for borrower, user_debts in new_simplified_debt.items():
        # debts is a dict of users this borrower owes to, like {'user1': 3, 'user2':8}
        for lender, value in user_debts.items():
            UserDebt.objects.create(group=group, value=value,
                                    borrower=User.objects.get(key=borrower),
                                    lender=User.objects.get(key=lender))

    response = json.dumps({'group_uuid': str(uome.group.uuid),
                           'user': user.key,
                           'uome_uuid': str(uome.uuid),
                           })

    logger.info('UOMe %s was accepted by user %s' % (str(uome_uuid), user_id))
    return HttpResponse(response, status=200)


@verify_author
@require_POST
def get_totals(request):
    """
    Used by a user to check the totals of users in the group
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_id = payload['user']
        user_signature = payload['user_signature']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user_id)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if the key is invalid
        logger.info('Request tried to get the totals for non-existent group %s'
                    'or user %s' % (group_uuid, user_id))
        return HttpResponseBadRequest()

    user_payload = json.dumps({'group_uuid': str(group.uuid),
                               'user': user.key,
                               })

    # todo: probably unnecessary because of the verify author decorator
    try:  # verify the signatures
        crypto.verify(user.key, user_signature, user_payload)
    except (crypto.InvalidKey, crypto.InvalidSignature):
        logger.info('Request with invalid signature or key by author %s' % user_id)
        return HttpResponseForbidden()

    # example: {'user1': val1, 'user2': val2}
    suggested_transactions = {}

    # todo: send the actual totals along with the suggested transactions
    if user.balance < 0:  # filter by borrower
        for debt in UserDebt.objects.filter(group=group, borrower=user):
            suggested_transactions[debt.lender.key] = debt.value

    elif user.balance > 0:  # filter by lender
        for debt in UserDebt.objects.filter(group=group, lender=user):
            suggested_transactions[debt.borrower.key] = debt.value

    response = json.dumps({'group_uuid': str(group.uuid),
                           'user': user.key,
                           'user_balance': user.balance,
                           'suggested_transactions': suggested_transactions,
                           })

    logger.info('Totals sent to user %s' % user_id)
    return HttpResponse(response, status=200)
