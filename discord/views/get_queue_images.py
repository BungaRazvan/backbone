from rest_framework.views import APIView
from django.http import HttpResponseBadRequest, JsonResponse
from discord.models import QueuePicture

from dataclasses import dataclass
from django.utils.decorators import method_decorator
from common.auth.decorators import require_token, validate_arguments


@dataclass
class Args:
    interval_name: str
    channel_name: str
    user_id: str
    number: int = 1
    delete: bool = False


class GetQueueImages(APIView):

    @method_decorator([require_token(app_name="discord"), validate_arguments(Args)])
    def get(self, request, args: Args):
        interval_name = args.interval_name
        channel_name = args.channel_name
        user_id = args.user_id
        number = args.number
        delete = args.delete

        picture = QueuePicture.objects.filter(
            qp_interval_id__qi_name=interval_name,
            qp_interval_id__qi_user_id=user_id,
            qp_interval_id__qi_channel=channel_name,
        )[:number].values("qp_image", "qp_id")

        if not picture:
            return HttpResponseBadRequest("Cannot find image")

        if delete:
            QueuePicture.objects.get(pk=picture[0]["qp_id"]).delete()

        return JsonResponse({"picture": picture[0]})
