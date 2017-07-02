from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
import json

from .models import Group


@require_GET
def echo_group(request):
    return HttpResponse(request.GET['group_name'])


@require_POST
def register_group(request):
    try:
        data = json.loads(request.POST['blob'])
    except json.JSONDecodeError:
        return HttpResponseBadRequest()

    try:
        group_name = data['group_name']
        group_key = data['group_key']
    except KeyError:
        return HttpResponseBadRequest  # Missing attributes

    if group_key != request.POST['author']:
        return HttpResponseBadRequest  #

    # create the group in the DB
    # TODO: limit the length of the group name?
    group = Group.objects.create(name=group_name, key=group_key)

    # response will be signed by Django middleware
    return HttpResponse(json.dumps({'group_uuid': group.uuid,
                                    'group_name': group.name,
                                    'group_key': group.key}))
