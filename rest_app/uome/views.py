import json
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_POST

from common.decorators import verify_author
from rest_app.models import Group, User, UOMe, UOME_DESCRIPTION_MAX_LENGTH

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
        user = payload['user']
        borrower = payload['borrower']
        value = payload['value']
        description = payload['description']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if request.POST['author'] != user:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
        user = User.objects.get(group=group, key=user)
        borrower = User.objects.get(group=group, key=borrower)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if key is not valid
        logger.info('Request tried to issue uome for non-existent group %s'
                    ', user %s or borrower %s' % (group_uuid, user, borrower))
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

    # logger.info('New user %s has been registered to group %s' % (user_key, group_uuid))
    return HttpResponse(response, status=201)
