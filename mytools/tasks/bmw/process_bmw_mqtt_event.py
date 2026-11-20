from datetime import datetime, timezone
import json

import logging

from celery import shared_task
from django.db import IntegrityError
from django.utils.dateparse import parse_datetime

from mytools.models import BMWCarDataEvent, Vehicle

logger = logging.getLogger(__name__)


@shared_task(max_retries=3, ignore_result=True)
def process_bmw_mqtt_event(topic: str, raw_payload: str):

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON payload: {e}")
        return

    if "status" in topic.lower() or "connected" in payload:
        logger.info(f"Ignored bridge status message on topic {topic}: {payload}")
        return

    vin = payload.get("vin") or payload.get("vehicleIdentificationNumber")

    if not vin:
        parts = topic.split("/")

        if len(parts) > 1:
            vin = parts[-1]

    vehicle = None

    if vin:
        vehicle = Vehicle.objects.filter(vin=vin).first()

    event_type = None
    data_block = payload.get("data", {})
    raw_timestamp = None
    event_timestamp = None

    if isinstance(data_block, dict) and data_block:
        # Grabs the first signal path key (e.g., "vehicle.cabin.door.row2.passenger.isOpen")
        event_type = list(data_block.keys())[0]

        raw_timestamp = data_block[event_type].get("timestamp")

    if not raw_timestamp:
        raw_timestamp = payload.get("timestamp") or payload.get("timeOfMostRecentDrive")

    if isinstance(raw_timestamp, (int, float)):
        if raw_timestamp > 1e12:  # Milliseconds check
            raw_timestamp = raw_timestamp / 1000.0

        event_timestamp = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)

    elif isinstance(raw_timestamp, str):
        event_timestamp = parse_datetime(raw_timestamp)

    try:
        BMWCarDataEvent.objects.create(
            vehicle=vehicle,
            event_type=event_type,
            timestamp=event_timestamp,
            payload=payload,
            processed=False,
        )
    except IntegrityError:
        logger.debug(f"Ignored duplicate BMW event [{event_type}]")
