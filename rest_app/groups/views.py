from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET

import json
import logging

from .models import Group

logger = logging.getLogger(__name__)


@require_POST
def register(request):
    try:
        author = request.POST['author']
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

    if group_key != author:
        logger.info('Request author not authorized')
        return HttpResponseBadRequest()

    # create the group in the DB
    # TODO: limit the length of the group name?
    group = Group.objects.create(name=group_name, key=group_key)

    # response will be signed by Django middleware
    logger.info('New group has been registered')
    return HttpResponse(json.dumps({'group_uuid': str(group.uuid),
                                    'group_name': group.name,
                                    'group_key': group.key}),
                        status=201)
