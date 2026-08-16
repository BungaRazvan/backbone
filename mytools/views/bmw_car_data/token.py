from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from common.auth.decorators import validate_arguments, require_token
from rest_framework import status
from dataclasses import dataclass

from common.lib.bmw_car_data import BMWCarDataClient
from typing import Optional
import time
import requests
from django.conf import settings

from .utils import (
    set_cookies,
    COOKIE_ACCESS_TOKEN,
    COOKIE_EXPIRES_AT,
    COOKIE_REFRESH_TOKEN,
)


@dataclass
class Args:
    device_code: str
    vin: Optional[str] = None


class BMWCarDataAuthTokenView(APIView):

    @method_decorator([require_token(app_name="mytools"), validate_arguments(Args)])
    def post(self, request, args: Args):

        client = BMWCarDataClient()
        client.access_token = request.COOKIES.get(COOKIE_ACCESS_TOKEN)
        client.refresh_token = request.COOKIES.get(COOKIE_REFRESH_TOKEN)
        expires_at_cookie = request.COOKIES.get(COOKIE_EXPIRES_AT)

        if expires_at_cookie:
            try:
                client.expires_at = float(expires_at_cookie)
            except ValueError:
                client.expires_at = None

        if (
            client.access_token
            and client.expires_at
            and time.time() < client.expires_at
        ):
            return Response(
                {"detail": "Session already active and valid."},
                status=status.HTTP_200_OK,
            )

        if client.refresh_token:
            try:
                client.refresh_access_token()
            except requests.RequestException as e:
                client.refresh_token = None
                response = Response(
                    {"error": f"Refreshing authentication failed: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
                response.delete_cookie(COOKIE_ACCESS_TOKEN)
                response.delete_cookie(COOKIE_REFRESH_TOKEN)
                response.delete_cookie(COOKIE_EXPIRES_AT)
                return response

        if not client.access_token:
            try:
                client.get_tokens_from_device_code(args.device_code)
            except requests.RequestException as e:
                return Response(
                    {"error": f"Token authentication failed: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        response = Response(
            {"detail": "Authentificated succesfully"}, status=status.HTTP_200_OK
        )
        set_cookies(response, client)

        return response
