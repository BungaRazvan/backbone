from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common.utils import get_api_key
from common.models import AppToken


class GenericAppTokenAuthentication(BaseAuthentication):
    """Generic DRF authentication class for AppTokens.

    Expects `app_name` to be set by a subclass or factory.
    """

    app_name = None

    def authenticate(self, request):
        native_request = request._request
        key = get_api_key(native_request)

        if not key:
            raise AuthenticationFailed("Missing API token")

        lookup_kwargs = {"at_app_token": key, "at_is_active": True}
        # Only filter by app_name if one was explicitly provided
        if self.app_name:
            lookup_kwargs["at_app_name"] = self.app_name

        try:
            token = AppToken.objects.get(**lookup_kwargs)
        except AppToken.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive token")

        return (None, token)


def app_auth(name: str):
    """Dynamically generates a GenericAppTokenAuthentication class configured for an app_name."""

    return type(
        f"{name.capitalize()}AppTokenAuthentication",
        (GenericAppTokenAuthentication,),
        {"app_name": name},
    )
