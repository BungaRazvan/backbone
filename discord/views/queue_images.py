import json

from django.views import View

from discord.models import QueuePictures, QueueIntervals
from django.http import JsonResponse


class QueueImages(View):
    http_method_names = ["post"]

    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Extract required fields
        interval_name = body.get("interval_name")
        channel_name = body.get("channel_name")
        user_id = body.get("user_id")
        urls = body.get("urls")
        at = body.get("at")

        # Optional
        interval_description = body.get("interval_description")

        if not all([interval_name, channel_name, user_id, urls, at]):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        # Check or create interval
        interval, created = QueueIntervals.objects.get_or_create(
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
            QueuePictures(qp_image=url, qp_interval_id=interval) for url in urls
        ]
        QueuePictures.objects.bulk_create(queue_images, batch_size=20)

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
