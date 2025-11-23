from django.db import models


class YoutubeSong(models.Model):
    class Meta:
        app_label = "discord"
        db_table = "youtube_song"

    ys_id = models.AutoField(primary_key=True)
    ys_url = models.TextField(null=False, blank=False)
    ys_playlist = models.ForeignKey(
        "discord.YoutubePlaylist",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="songs",
    )

    def __str__(self):
        return f"{self.ys_playlist.yp_name} - {self.ys_url}"
