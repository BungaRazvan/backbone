from django.db import models


class QueuePicture(models.Model):
    class Meta:
        db_table = "queue_pictures"
        app_label = "discord"

    qp_id = models.AutoField(primary_key=True)
    qp_image = models.URLField()
    qp_created_at = models.DateTimeField()

    qp_interval = models.ForeignKey(
        "discord.QueueInterval",
        on_delete=models.CASCADE,
        to_field="qi_id",
        db_column="qp_interval_id",
        related_name="pictures",
    )
