from django.db import models
from common.mixins import AutoStrMixin


class BMWCarDataEvent(AutoStrMixin, models.Model):

    class Meta:
        db_table = "bmw_cardata_events"
        ordering = ["-timestamp"]
        app_label = "mytools"

    vehicle = models.ForeignKey(
        "mytools.Vehicle",
        on_delete=models.CASCADE,
        related_name="bmw_raw_events",
        db_index=True,
        null=True,
        blank=True,
    )

    event_type = models.CharField(max_length=150, db_index=True, blank=True, null=True)
    timestamp = models.DateTimeField(db_index=True, null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "bmw_cardata_events"
        ordering = ["-timestamp"]
