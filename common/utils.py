from functools import wraps
from django.http import HttpResponseForbidden
from common.models import AppToken


def require_token(app_name=None):
    """
    Decorator to require a valid API token.
    Works for both function-based and class-based views.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if hasattr(args[0], "request"):
                self = args[0]
                request = self.request
            else:
                request = args[0]

            key = request.headers.get("X-API-KEY") or request.META.get("HTTP_X_API_KEY")

            if not key:
                return HttpResponseForbidden("Missing API token")

            try:
                token = AppToken.objects.get(
                    at_app_token=key, at_is_active=True, at_app_name=app_name
                )
            except AppToken.DoesNotExist:
                return HttpResponseForbidden("Invalid or inactive token")

            request.app_token = token
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
