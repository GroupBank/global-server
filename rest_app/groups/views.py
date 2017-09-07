import json
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from common.decorators import verify_author
from rest_app.models import Group, User

logger = logging.getLogger(__name__)


@verify_author
@require_POST
def register(request):
    """
    Used to register a new group server in the system
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_name = payload['group_name']
        group_key = payload['group_key']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    if group_key != request.POST['author']:
        logger.info('Request author not authorized')
        return HttpResponseBadRequest()

    # create the group in the DB
    # TODO: limit the length of the group name?
    group = Group.objects.create(name=group_name, key=group_key)

    # response will be signed by Django middleware
    logger.info('New group %s has been registered' % group.uuid)
    return HttpResponse(json.dumps({'group_uuid': str(group.uuid),
                                    'group_name': group.name,
                                    'group_key': group.key}),
                        status=201)


@verify_author
@require_POST
def register_user(request):
    """
    Used by a group server to register a new user associated to it
    """
    try:
        payload = json.loads(request.POST['payload'])
    except json.JSONDecodeError:
        logger.info('Malformed request')
        return HttpResponseBadRequest()

    try:
        group_uuid = payload['group_uuid']
        user_key = payload['user_key']
    except KeyError:
        logger.info('Request with missing attributes')
        return HttpResponseBadRequest()

    try:  # check that the group exists and get it
        group = Group.objects.get(pk=group_uuid)
    except (ValidationError, ObjectDoesNotExist):  # ValidationError if key is not valid
        logger.info('Request tried to create user for non-existent group %s' % group_uuid)
        return HttpResponseBadRequest()

    if request.POST['author'] != group.key:
        logger.info('Request made by unauthorized author %s' % request.POST['author'])
        return HttpResponse('401 Unauthorized', status=401)

    user = User.objects.create(group=group, key=user_key)

    logger.info('New user %s has been registered to group %s' % (user_key, group_uuid))
    return HttpResponse(json.dumps({'group_uuid': str(group.uuid),
                                    'user': user.key}),
                        status=201)
