import json
import hashlib

from django.db import models
from common.mixins import AutoStrMixin


def compute_bmw_event_fingerprint(
    vehicle_id, event_type, event_timestamp, payload
) -> str:
    signal_value = None
    entity_id = None

    if isinstance(payload, dict):
        entity_id = payload.get("entityId")
        data_block = payload.get("data")
        if (
            isinstance(data_block, dict)
            and event_type
            and isinstance(data_block.get(event_type), dict)
        ):
            signal_value = data_block[event_type].get("value")

    ts_str = (
        event_timestamp.isoformat()
        if hasattr(event_timestamp, "isoformat")
        else (str(event_timestamp) if event_timestamp else None)
    )
    canonical = json.dumps(
        {
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "timestamp": ts_str,
            "entity_id": entity_id,
            "value": signal_value,
        },
        sort_keys=True,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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

    session = models.ForeignKey(
        "mytools.VehicleSession",
        on_delete=models.SET_NULL,
        related_name="sessions",
        blank=True,
        null=True,
    )

    event_type = models.CharField(max_length=150, db_index=True, blank=True, null=True)
    timestamp = models.DateTimeField(db_index=True, null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False, db_index=True)
    fingerprint = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        db_table = "bmw_cardata_events"
        ordering = ["-timestamp"]

    @property
    def event_time(self):
        return self.timestamp or self.received_at

    def save(self, *args, **kwargs):

        if not self.fingerprint:
            self.fingerprint = compute_bmw_event_fingerprint(
                self.vehicle_id, self.event_type, self.timestamp, self.payload
            )

        super().save(*args, **kwargs)
