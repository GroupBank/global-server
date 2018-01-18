import logging

from django.http import HttpResponseBadRequest, HttpResponseForbidden
from functools import wraps

import groupbank_crypto.ec_secp256k1 as crypto

logger = logging.getLogger(__name__)


# decorator for verifying the payload is signed by the author of the request
def verify_author(view):

    @wraps(view)  # to get features like showing the original function name in trace backs
    def wrapper(request):
        # https://docs.djangoproject.com/en/1.11/topics/http/middleware/#process-view
        # verify the JSON B64 string. return None if it's fine,
        # return an HTTPResponse with an error if not

        try:
            author, signature, payload = request.POST['author'], request.POST['signature'], request.POST['payload']
        except KeyError:
            logger.info('Request with missing author, signature or payload')
            return HttpResponseBadRequest()

        # get user pubkey
        # what if the author CAN'T already be registered? i.e.: group key
        # maybe check view_func and ignore a few?
        # or let the view itself verify if the author is registered...

        # NOTE: This does not verify if the signer is authorized for the operation.
        #       It only verifies if the signature matches the given pub key

        try:
            crypto.verify(author, signature, payload)
            return view(request)
        except (crypto.InvalidSignature, crypto.InvalidKey):
            logger.info('Request with invalid author key or signature')
            return HttpResponseForbidden()
            # or 401 Unauthorized...

    return wrapper
