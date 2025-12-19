from django.db import models


class MinecraftPlayer(models.Model):

    class Meta:
        db_table = "minecraft_players"
        app_label = "discord"

    mp_id = models.AutoField(primary_key=True)
    mp_uuid = models.UUIDField(null=False, blank=False)
    mp_mc_name = models.CharField(max_length=255, null=False, blank=False)
    mp_ds_user_id = models.CharField(max_length=255, null=True, blank=True)
    mp_ds_quild_id = models.CharField(max_length=255, null=True, blank=True)
    mp_mcs_server = models.ForeignKey(
        "discord.MinecraftServer",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        db_column="mp_mcs_server_id",
    )
