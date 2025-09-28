from django.views import View
from django.http import HttpResponseBadRequest, JsonResponse
from discord.models import QueuePictures


class GetQueueImages(View):
    http_method_names = ["get"]

    def get(self, request):
        args = request.GET
        interval_name = args.get("interval_name")
        channel_name = args.get("channel_name")
        user_id = args.get("user_id")
        number = (args.get("number") or 1,)
        delete = args.get("delete") or False

        if not interval_name or not channel_name or not user_id:
            return HttpResponseBadRequest()

        picture = QueuePictures.objects.filter(
            qp_interval_id__qi_name=interval_name,
            qp_interval_id__qi_user_id=user_id,
            qp_interval_id__qi_channel=channel_name,
        )[:number].values("qp_image", "qp_id")

        if not picture:
            raise Exception("Cannot find image")

        if delete:
            QueuePictures.objects.get(pk=picture[0]["qp_id"]).delete()

        return JsonResponse({"picture": picture[0]})
