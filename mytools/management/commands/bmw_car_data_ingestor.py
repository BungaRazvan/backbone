import json
import logging
import time
from datetime import datetime, timezone
from django.conf import settings
from django.core.management.base import BaseCommand
import paho.mqtt.client as mqtt

from mytools.models import BMWCarDataEvent
from common.lib.bmw_car_data import BMWCarDataClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Listens to BMW MQTT live stream and saves raw events to BMWCarDataEvent model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            type=str,
            default=getattr(
                settings,
                "BMW_MQTT_HOST",
                "",
            ),
        )
        parser.add_argument(
            "--port",
            type=int,
            default=getattr(settings, "BMW_MQTT_PORT", 9000),
        )
        parser.add_argument(
            "--username",
            type=str,
            default=getattr(settings, "BMW_GCID_USERNAME", ""),
            help="Your BMW GCID username from the portal",
        )
        parser.add_argument(
            "--topic",
            type=str,
            default=getattr(settings, "BMW_MQTT_TOPIC", ""),
            help="Assigned topic (e.g. GCID/VIN or GCID/+)",
        )

    def handle(self, *args, **options):
        host = options["host"]
        port = options["port"]
        username = options["username"]
        topic = options["topic"]

        if not username:
            self.stderr.write(self.style.ERROR("Missing --username (GCID) argument."))
            return

        # Initialize BMW Client
        bmw_client = BMWCarDataClient()

        # Initialize MQTT v5 client over TLS
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5,
        )
        client.tls_set()

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully connected to BMW Broker at {host}:{port}"
                    )
                )
                client.subscribe(topic, qos=1)
                self.stdout.write(self.style.SUCCESS(f"Subscribed to topic: {topic}"))
            else:
                logger.error(f"Connection failed with reason code: {reason_code}")

        def on_disconnect(client, userdata, flags, reason_code, properties):
            logger.warning(
                f"Disconnected from stream (rc={reason_code}). Reauthenticating..."
            )
            while True:
                try:
                    fresh_id_token = bmw_client.ensure_valid_id_token()
                    client.username_pw_set(username=username, password=fresh_id_token)
                    client.reconnect()
                    break
                except Exception as e:
                    logger.error(
                        f"Reconnection attempt failed: {e}. Retrying in 10s..."
                    )
                    time.sleep(10)

        def on_message(client, userdata, msg):
            try:
                raw_bytes = msg.payload.decode("utf-8")

                BMWCarDataEvent.objects.create(
                    bcde_vin="WBA6N320X0FK24381",
                    bcde_timestamp=datetime.now(timezone.utc),
                    bcde_source=BMWCarDataEvent.EventSource.MQTT_STREAM,
                    bcde_payload=raw_bytes,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{datetime.now().strftime('%H:%M:%S')}] Saved stream event for VIN {settings.BMW_MQTT_TOPIC} ({msg.topic})"
                    )
                )

            except Exception as e:
                logger.error(
                    f"Failed to ingest stream event from {msg.topic}: {str(e)}"
                )

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        # Obtain initial ID Token (polls user code if initial setup needed)
        self.stdout.write("Checking BMW authentication status...")
        initial_id_token = bmw_client.ensure_valid_id_token()

        print(initial_id_token)
        # Set MQTT Credentials
        client.username_pw_set(username=username, password=initial_id_token)

        self.stdout.write(f"Connecting to BMW MQTT Stream at {host}:{port}...")
        client.connect(host, port, keepalive=30)
        client.loop_forever()
