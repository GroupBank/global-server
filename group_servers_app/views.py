from django.http import HttpResponse
from django.views.decorators.http import require_POST, require_GET


@require_GET
def echo_group(request):
    return HttpResponse(request.GET['group_name'])

"""
@require_POST
def register_group(request):
    # convert the message into the request object
    try:
        request = msg.RegisterGroup.load_request(request.POST['data'])
    except DecodeError:
        return HttpResponseBadRequest()

    # verify the signature
    try:
        msg.RegisterGroup.verify(request.group_key, 'group', request.group_signature,
                                 group_name=request.group_name,
                                 group_key=request.group_key)
    except InvalidSignature:
        return HttpResponse('401 Unauthorized', status=401)  # There's no class for it

    # signature is correct, create the group
    # TODO: limit the length of the group name?
    group = Group.objects.create(name=request.group_name, key=request.group_key)

    # group created, create the response object
    signature = msg.RegisterGroup.sign(settings.PRIVATE_KEY, 'main',
                                       group_uuid=group.uuid,
                                       group_name=group.name,
                                       group_key=group.key)

    response = msg.RegisterGroup.make_response(group_uuid=str(group.uuid),
                                               main_signature=signature)

    # send the response, the status for success is 201 Created
    return HttpResponse(response.dumps(), status=201)
"""