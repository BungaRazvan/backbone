from functools import wraps
from django.http import HttpResponseForbidden
from common.models import AppToken


def get_api_key(request):

    header_keys = ["X-API-KEY", "x-api-key", "HTTP_X_API_KEY"]

    for key in header_keys:
        value = request.headers.get(key)
        if value:
            return value

        value = request.META.get(key)
        if value:
            return value

    return None


from functools import wraps
from django.http import HttpResponseForbidden
from .models import AppToken
from .utils import get_api_key


def require_token(app_name=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):

            # CBV method: (self, request, ...)
            if hasattr(args[0], "request"):
                request = args[0].request
            else:
                request = args[0]

            key = get_api_key(request)

            if not key:
                return HttpResponseForbidden("Missing API token")

            try:
                token = AppToken.objects.get(
                    at_app_token=key,
                    at_is_active=True,
                    at_app_name=app_name,
                )
            except AppToken.DoesNotExist:
                return HttpResponseForbidden("Invalid or inactive token")

            request.app_token = token
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
