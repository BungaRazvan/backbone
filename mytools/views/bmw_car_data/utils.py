from django.http.response import HttpResponse
from django.http.request import HttpRequest
from common.lib.bmw_car_data import BMWCarDataClient
from django.conf import settings
import time

COOKIE_PREFIX = "bmw_car_data_"
COOKIE_ACCESS_TOKEN = f"{COOKIE_PREFIX}_access_token"
COOKIE_REFRESH_TOKEN = f"{COOKIE_PREFIX}refresh_token"
COOKIE_EXPIRES_AT = f"{COOKIE_PREFIX}expires_at"


def set_cookies(response: HttpResponse, client: BMWCarDataClient):
    if client.access_token:
        response.set_cookie(
            key=COOKIE_ACCESS_TOKEN,
            value=client.access_token,
            httponly=True,
            secure=settings.ENV != "dev",
            samesite="Lax" if settings.ENV == "dev" else "None",
            max_age=3600,
        )

    if client.refresh_token:
        response.set_cookie(
            key=COOKIE_REFRESH_TOKEN,
            value=client.refresh_token,
            httponly=True,
            secure=settings.ENV != "dev",
            samesite="Lax" if settings.ENV == "dev" else "None",
            max_age=30 * 86400,
        )

    if client.expires_at:
        response.set_cookie(
            key=COOKIE_EXPIRES_AT,
            value=str(client.expires_at),
            httponly=True,
            secure=settings.ENV != "dev",
            samesite="Lax" if settings.ENV == "dev" else "None",
            max_age=3600,
        )

    return response


def check_cookies(request: HttpRequest) -> bool:
    access_token = request.COOKIES.get(COOKIE_ACCESS_TOKEN)
    expires_at_cookie = request.COOKIES.get(COOKIE_EXPIRES_AT)

    if not access_token:
        return False

    try:
        expires_at = float(expires_at_cookie)
    except ValueError:
        return False

    if time.time() + 60 >= expires_at:
        return False

    return True


def build_client(request: HttpRequest) -> BMWCarDataClient:
    client = BMWCarDataClient()
    client.access_token = request.COOKIES.get(COOKIE_ACCESS_TOKEN)
    client.refresh_token = request.COOKIES.get(COOKIE_REFRESH_TOKEN)
    client.expires_at = float(request.COOKIES.get(COOKIE_EXPIRES_AT))

    return client
