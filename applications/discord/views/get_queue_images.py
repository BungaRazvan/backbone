from applications.base import BaseView
from models.discord import QueuePictures


class GetQueueImages(BaseView):
    http_method_names = ['get']

    def execute_get(self, interval_name, channel_name, user_id, number=1, delete=False):
        picture = QueuePictures.objects.filter(
            qp_interval_id__qi_name=interval_name,
            qp_interval_id__qi_user_id=user_id,
            qp_interval_id__qi_channel=channel_name,
        )[:number].values('qp_image', 'qp_id')

        if not picture:
            raise Exception('Cannot find image')

        if delete:
            QueuePictures.objects.get(pk=picture[0]['qp_id']).delete()

        return {'picture': picture[0]}
