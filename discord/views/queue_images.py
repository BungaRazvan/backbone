from applications.base import BaseView
from models.discord import QueuePictures, QueueIntervals


class QueueImages(BaseView):
    http_method_names = ["post"]

    def execute_post(
        self, interval_name, channel_name, user_id, urls, at, interval_description=None
    ):
        new_queue = False

        try:
            interval = QueueIntervals.objects.get(
                qi_user_id=user_id,
                qi_name=interval_name,
                qi_channel=channel_name,
            )
        except QueueIntervals.DoesNotExist:
            interval = QueueIntervals.objects.create(
                qi_user_id=user_id,
                qi_name=interval_name,
                qi_channel=channel_name,
                qi_description=interval_description,
                qi_at=at,
            )
            new_queue = True

        queue_images = []

        for url in urls:
            queue_images.append(QueuePictures(qp_image=url, qp_interval_id=interval))

        QueuePictures.objects.bulk_create(queue_images, batch_size=20)

        if new_queue:
            return f"New Queue Created"

        return f"Successfully added more images to queue: **{interval.qi_name}**"
