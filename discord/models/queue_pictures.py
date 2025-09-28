from django.db import models


class QueuePictures(models.Model):
    class Meta:
        db_table = "queue_pictures"
        app_label = "discord"

    qp_id = models.AutoField(primary_key=True)
    qp_image = models.CharField(max_length=255)
    qp_created_at = models.DateTimeField()

    qp_interval_id = models.ForeignKey(
        "QueueIntervals",
        on_delete=models.DO_NOTHING,
        to_field="qi_id",
        db_column="qp_interval_id",
    )
