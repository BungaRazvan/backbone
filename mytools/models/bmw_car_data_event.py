from django.db import models
from common.mixins import AutoStrMixin


class BMWCarDataEvent(AutoStrMixin, models.Model):
    """Raw event store for all incoming BMW telematics payloads (CSV, REST, or MQTT)."""

    class EventSource(models.TextChoices):
        CSV_ARCHIVE = "CSV_ARCHIVE", "CSV Archive Export"
        REST_API = "REST_API", "REST API Snapshot"
        MQTT_STREAM = "MQTT_STREAM", "Live MQTT Stream"

    class Meta:
        db_table = "bmw_cardata_events"
        app_label = "mytools"
        ordering = ["bcde_timestamp"]
        indexes = [
            models.Index(fields=["bcde_vin", "bcde_timestamp"]),
            models.Index(fields=["bcde_source", "bcde_processed"]),
        ]

    bcde_vin = models.CharField(max_length=17, db_index=True)
    bcde_timestamp = models.DateTimeField(help_text="UTC timestamp when event occurred")

    bcde_source = models.CharField(
        max_length=20,
        choices=EventSource.choices,
        default=EventSource.CSV_ARCHIVE,
    )

    # Stores the raw dictionary / row / API payload without alteration
    bcde_payload = models.JSONField(
        help_text="Unmodified raw JSON event data or converted CSV row key-values"
    )

    # Pipeline Processing Tracking
    bcde_processed = models.BooleanField(
        default=False,
        help_text="True if this raw event has been parsed into derived models",
    )
    bcde_processed_at = models.DateTimeField(null=True, blank=True)

    bcde_created_at = models.DateTimeField(auto_now_add=True)
