from django.db import models


class MinecraftStat(models.Model):
    class Meta:
        db_table = "minecraft_stats"
        app_label = "discord"

    mst_id = models.AutoField(primary_key=True)
    mst_data = models.JSONField()
    mst_timestamp = models.DateTimeField(auto_now_add=True)
    mst_player = models.OneToOneField(
        "discord.MinecraftPlayer",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        db_column="mst_player_id",
        related_name="stat",
    )
