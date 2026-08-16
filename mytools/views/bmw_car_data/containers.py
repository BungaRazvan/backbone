from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from common.auth.decorators import validate_arguments, require_token
from common.lib.bmw_car_data import BMWCarDataClient
from dataclasses import dataclass, asdict
from typing import Optional, Union, List

import time

from .utils import build_client, check_cookies, set_cookies
from django.http import HttpRequest
import requests


@dataclass
class ArgsGet:
    containerId: Optional[str] = None


@dataclass
class ArgsDelete:
    containerId: str


@dataclass
class ArgsPost:
    name: str
    purpose: str
    technicalDescriptors: List[str]


class BMWCarDataContainersView(APIView):

    @method_decorator([require_token(app_name="mytools"), validate_arguments(ArgsGet)])
    def get(self, request: HttpRequest, args: ArgsGet):

        if not check_cookies(request):
            return Response(
                {
                    "detail": "Invalid Cookies",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        client = build_client(request)
        print(client.access_token)
        print(client.refresh_token)
        print(client.expires_at)

        try:
            if args.containerId:
                res = client.get(f"customers/containers/{args.containerId}")
            else:
                res = client.get("customers/containers")

            res.raise_for_status()
            response = Response(res.json(), status=res.status_code)
            set_cookies(response, client)

            return response

        except requests.RequestException as e:
            return Response(
                {"error": str(e)},
                status=(
                    e.response.status_code
                    if e.response
                    else status.HTTP_502_BAD_GATEWAY
                ),
            )

    @method_decorator([require_token(app_name="mytools"), validate_arguments(ArgsPost)])
    def post(self, request: HttpRequest, args: ArgsPost):
        if not check_cookies(request):
            return Response(
                {"detail": "Invalid Cookies"},
                status=status.HTTP_403_FORBIDDEN,
            )

        client = build_client(request)

        try:
            res = client.request("POST", "customers/containers", json=asdict(args))
            res.raise_for_status()

            response = Response(res.json(), status=res.status_code)
            set_cookies(response, client)
            return response

        except requests.RequestException as e:
            error_payload = (
                e.response.json()
                if e.response and e.response.content
                else {"error": str(e)}
            )
            return Response(
                error_payload,
                status=(
                    e.response.status_code
                    if e.response
                    else status.HTTP_502_BAD_GATEWAY
                ),
            )

    @method_decorator(
        [require_token(app_name="mytools"), validate_arguments(ArgsDelete)]
    )
    def delete(self, request: HttpRequest, args: ArgsDelete):
        if not check_cookies(request):
            return Response(
                {"detail": "Invalid Cookies"},
                status=status.HTTP_403_FORBIDDEN,
            )

        client = build_client(request)

        try:
            res = client.request("DELETE", f"customers/containers/{args.containerId}")
            res.raise_for_status()

            response = Response(res.json(), status=res.status_code)
            set_cookies(response, client)
            return response

        except requests.RequestException as e:
            error_payload = (
                e.response.json()
                if e.response and e.response.content
                else {"error": str(e)}
            )
            return Response(
                error_payload,
                status=(
                    e.response.status_code
                    if e.response
                    else status.HTTP_502_BAD_GATEWAY
                ),
            )
