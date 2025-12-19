from django.db import models


class MinecraftServer(models.Model):
    class Meta:
        db_table = "minecraft_servers"
        app_label = "discord"

    mcs_id = models.AutoField(primary_key=True)
    mcs_name = models.CharField(max_length=255, blank=False, null=False)

    def __str__(self):
        return f"MinecraftServer(mcs_id={self.mcs_id}, mcs_name={self.mcs_name})"
