from django.db import models


class BaseYoutubePlaylist(models.Model):

    class Meta:
        abstract = True

    yp_name = models.CharField(max_length=255, null=False, blank=False)
    yp_videos = models.JSONField()
