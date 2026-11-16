import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from mytools.tasks.bmw.process_bmw_mqtt_event import process_bmw_mqtt_event

from django.conf import settings


class Command(BaseCommand):
    help = "Run the BMW MQTT client to listen for events and process them."

    def handle(self, *args, **options):
        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                print("Connected to MQTT broker successfully.")
                client.subscribe("bmw/#")
            else:
                print(f"Failed to connect to MQTT broker. Return code: {rc}")

        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                payload = msg.payload.decode("utf-8")

                process_bmw_mqtt_event.delay(topic, payload)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error handling incoming MQTT message: {e}")
                )

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message

        broker_host = settings.BMW_CAR_DATA_MQTT_BROKER_HOST
        broker_port = settings.BMW_CAR_DATA_MQTT_BROKER_PORT
        self.stdout.write(
            f"Connecting to MQTT broker at {broker_host}:{broker_port}..."
        )
        client.connect(broker_host, broker_port, keepalive=60)

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("MQTT client stopped."))
            client.disconnect()
