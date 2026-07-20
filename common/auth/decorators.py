from functools import wraps
from django.http import HttpResponseForbidden, HttpRequest

from common.utils import get_api_key
from common.models import AppToken

from rest_framework_dataclasses.serializers import DataclassSerializer
from rest_framework.request import Request


def require_token(view_func=None, *, app_name):
    """
    Robust decorator to require a valid AppToken.
    Works perfectly with FBVs, CBVs, and Django's method_decorator.
    """

    def _execute_decorator(view_func, *args, **kwargs):
        """Core logic that extracts the request and validates the database token."""
        request = None

        # Safely extract the HttpRequest object across FBVs, CBVs, and method_decorator
        for arg in args:
            if isinstance(arg, HttpRequest):
                request = arg
                break
        else:
            if len(args) > 1 and isinstance(args[1], HttpRequest):
                request = args[1]
            elif args and isinstance(args[0], Request):
                request = args[0]._request
            elif args and hasattr(args[0], "request"):
                request = args[0].request

        if not request:
            raise ValueError(
                "require_token decorator couldn't find the HttpRequest object."
            )

        key = get_api_key(request)
        if not key:
            return HttpResponseForbidden("Missing API token")

        try:
            # Build query dynamically depending on whether app_name was provided
            lookup_kwargs = {"at_app_token": key, "at_is_active": True}
            if app_name:
                lookup_kwargs["at_app_name"] = app_name

            token = AppToken.objects.get(**lookup_kwargs)
        except AppToken.DoesNotExist:
            return HttpResponseForbidden("Invalid or inactive token")

        # Attach the token to the request and execute the view
        request.app_token = token
        return view_func(*args, **kwargs)

    # Handles usage without parentheses: @require_token
    if view_func is not None and callable(view_func):

        @wraps(view_func)
        def wrapper(*args, **kwargs):
            return _execute_decorator(view_func, *args, **kwargs)

        return wrapper

    # Handles usage with arguments: @require_token(app_name="mytools")
    def decorator(actual_view_func):
        @wraps(actual_view_func)
        def wrapper(*args, **kwargs):
            return _execute_decorator(actual_view_func, *args, **kwargs)

        return wrapper

    return decorator


def validate_arguments(dataclass_cls):
    """
    Universal DRF Decorator: Validates incoming arguments against a DataclassSerializer.
    Automatically handles body data (POST/PUT/PATCH) or query strings (GET/DELETE).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method in ["POST", "PUT", "PATCH"]:
                incoming_data = request.POST
            else:
                incoming_data = request.GET

            serializer = DataclassSerializer(
                data=incoming_data, dataclass=dataclass_cls
            )

            serializer.is_valid(raise_exception=400)
            kwargs["args"] = serializer.validated_data

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
