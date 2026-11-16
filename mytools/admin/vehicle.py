from django.core.serializers import json

from mytools.models import BMWCarDataEvent, Vehicle

from django.contrib import admin
from django.utils.html import format_html
import json


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vin", "make", "model", "year")
    search_fields = ("vin", "make", "model", "year")


@admin.register(BMWCarDataEvent)
class BMWCarDataEventAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "event_type", "timestamp", "received_at", "processed")
    search_fields = ("vehicle__vin", "event_type")
    list_filter = ("event_type", "processed", "vehicle")
    date_hierarchy = "timestamp"
    readonly_fields = ("formatted_payload", "received_at")

    def formatted_payload(self, obj):
        if not obj.payload:
            return "-"
        # Pretty-print JSON with 4 spaces indentation
        pretty_str = json.dumps(obj.payload, indent=4)
        # Render inside a styled monospace box for maximum readability
        return format_html(
            '<pre style="background: #1e1e1e; color: #dcdcdc; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; overflow-x: auto;">{}</pre>',
            pretty_str,
        )

    formatted_payload.short_description = "Payload (JSON)"
