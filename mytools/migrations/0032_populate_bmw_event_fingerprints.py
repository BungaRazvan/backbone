import hashlib
import json
from django.db import migrations


def _compute_fingerprint(vehicle_id, event_type, event_timestamp, payload) -> str:
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
        else (str(event_timestamp) if event_timestamp is not None else None)
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


def populate_and_delete_duplicates(apps, schema_editor):
    BMWCarDataEvent = apps.get_model("mytools", "BMWCarDataEvent")
    seen_fingerprints = set()
    duplicate_ids = []

    for row in (
        BMWCarDataEvent.objects.order_by("id")
        .values(
            "id",
            "vehicle_id",
            "event_type",
            "timestamp",
            "payload",
            "fingerprint",
            "session_id",
        )
        .iterator(chunk_size=500)
    ):
        fp = _compute_fingerprint(
            row["vehicle_id"],
            row["event_type"],
            row["timestamp"],
            row["payload"],
        )

        if fp in seen_fingerprints:
            # Keep the lowest id; only delete rows not already linked to a session
            if row["session_id"] is None:
                duplicate_ids.append(row["id"])
        else:
            seen_fingerprints.add(fp)
            if row["fingerprint"] != fp:
                BMWCarDataEvent.objects.filter(pk=row["id"]).update(fingerprint=fp)

    for i in range(0, len(duplicate_ids), 500):
        BMWCarDataEvent.objects.filter(id__in=duplicate_ids[i : i + 500]).delete()


class Migration(migrations.Migration):
    dependencies = [
        (
            "mytools",
            "0031_bmwcardataevent_fingerprint",
        ),  # Replace with your actual previous migration
    ]

    operations = [
        migrations.RunPython(
            populate_and_delete_duplicates, reverse_code=migrations.RunPython.noop
        ),
    ]
