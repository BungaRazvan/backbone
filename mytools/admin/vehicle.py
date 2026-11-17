import json

from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession

from django.contrib import admin
from django.utils.html import format_html


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


@admin.register(VehicleSession)
class VehicleSessionAdmin(admin.ModelAdmin):
    readonly_fields = ("formatted_payload", "created_at")
    exclude = ("merged_state",)
    list_display = (
        "vehicle",
        "activity_type",
        "started_at",
        "ended_at",
        "created_at",
    )

    @admin.display(description="Meged State")
    def formatted_payload(self, obj):
        if not obj.merged_state:
            return "-"

        pretty_str = json.dumps(
            obj.merged_state,
            indent=4,
        )

        return format_html(
            '<pre style="display: block; white-space: pre; margin: 0; '
            "background: #1e1e1e; color: #dcdcdc; padding: 12px; "
            "border-radius: 6px; font-family: monospace; font-size: 13px; "
            'line-height: 1.4; overflow-x: auto; max-height: 600px;">{}</pre>',
            pretty_str,
        )
