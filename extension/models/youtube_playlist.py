from django.db import models


class YoutubePlaylist(models.Model):
    class Meta:
        db_table = "youtube_playlist"
        app_label = "extension"

    yp_name = models.CharField(max_length=255)
    yp_videos = models.JSONField()
