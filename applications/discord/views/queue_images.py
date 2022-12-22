from applications.base import BaseView
from models.discord import QueuePictures, QueueIntervals


class QueueImages(BaseView):
	http_method_names = ['post']

	def execute_post(self, interval_name, channel_name, user_id, urls, at, interval_description):
		