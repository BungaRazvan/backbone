from typing import Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.utils.decorators import method_decorator

import requests
from dataclasses import dataclass

from common.auth.decorators import require_token, validate_arguments

from common.lib.bmw_car_data import BMWCarDataClient


@dataclass
class Args:
    scope: Optional[str] = None
    vin: Optional[str] = None


class BMWCarDataAuthDeviceCodeView(APIView):

    @method_decorator([require_token(app_name="mytools"), validate_arguments(Args)])
    def post(self, request, args: Args):

        client = BMWCarDataClient()

        try:
            device_data = client.request_device_code(args.scope)
            return Response(device_data, status=status.HTTP_200_OK)
        except requests.RequestException as e:
            return Response(
                {"error": f"Failed to request device code: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
