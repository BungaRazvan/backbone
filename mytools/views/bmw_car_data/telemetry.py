from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.utils.decorators import method_decorator
from common.auth.decorators import validate_arguments, require_token

from dataclasses import dataclass
from .utils import set_cookies, check_cookies, build_client


@dataclass
class Args:
    vin: str
    containerId: str


class BMWTelematicView(APIView):

    @method_decorator([validate_arguments(Args), require_token(app_name="mytools")])
    def get(self, request, args: Args):

        if not check_cookies(request):
            return Response(
                {
                    "detail": "Invalid Cookies",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        client = build_client(request)

        res = client.get(
            f"customers/vehicles/{args.vin}/telematicData?containerId={args.containerId}"
        )

        response = Response(res.json(), status=res.status_code)
        set_cookies(response, client)
        return response
