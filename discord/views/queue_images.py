import json

from rest_framework import APIView

from discord.models import QueuePicture, QueueInterval
from django.http import JsonResponse
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


class QueueImages(APIView):

    @method_decorator([require_token(app_name="discord"), validate_arguments(Args)])
    def post(self, request, args: Args):

        # Extract required fields
        interval_name = args.interval_name
        channel_name = args.channel_name
        user_id = args.user_id
        urls = args.urls
        at = args.at
        interval_description = args.interval_description

        # Check or create interval
        interval, created = QueueInterval.objects.get_or_create(
            qi_user_id=user_id,
            qi_name=interval_name,
            qi_channel=channel_name,
            defaults={
                "qi_description": interval_description,
                "qi_at": at,
            },
        )
        # Add images
        queue_images = [
            QueuePicture(qp_image=url, qp_interval_id=interval) for url in urls
        ]
        QueuePicture.objects.bulk_create(queue_images, batch_size=20)

        if created:
            return JsonResponse(
                {"message": "New Queue Created", "queue_name": interval.qi_name},
                status=201,
            )

        return JsonResponse(
            {
                "message": f"Added {len(urls)} images to queue",
                "queue_name": interval.qi_name,
            },
            status=200,
        )
