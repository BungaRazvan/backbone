from django.db import models


class YoutubePlaylists(models.Model):
    class Meta:
        db_table = "youtube_playlists"
        app_label = "extension"

    yp_name = models.CharField(max_length=255)
    yp_videos = models.JSONField()
