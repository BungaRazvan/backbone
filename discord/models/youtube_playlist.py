from django.db import models


class YoutubePlaylist(models.Model):
    class Meta:
        db_table = "youtube_playlist"
        app_label = "discord"

    yp_id = models.AutoField(primary_key=True)
    yp_name = models.CharField(max_length=255, null=False, blank=False)
    yp_user_id = models.TextField(null=False, blank=False)
    yp_guild_id = models.TextField(null=False, blank=False)

    def __str__(self):
        return f"{self.yp_name}"
