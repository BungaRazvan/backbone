from django.contrib import admin

from common.lib.pretty_json import PrettyJsonAdmin

from mytools.models import BMWCarDataEvent, Vehicle, VehicleSession


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vin", "make", "model", "year")
    search_fields = ("vin", "make", "model", "year")


@admin.register(BMWCarDataEvent)
class BMWCarDataEventAdmin(PrettyJsonAdmin, admin.ModelAdmin):
    list_display = (
        "vehicle",
        "event_type",
        "timestamp",
        "received_at",
        "processed",
        "fingerprint",
    )
    search_fields = ("vehicle__vin", "event_type")
    list_filter = ("processed", "vehicle", "timestamp", "event_type")
    date_hierarchy = "timestamp"
    readonly_fields = ("formatted_payload", "received_at")
    exclude = ("payload",)

    actions = ["unprocess"]

    @admin.display(description="Payload (JSON)")
    def formatted_payload(self, obj):
        return self.format_json(obj, "payload")

    @admin.action(description="Mark as unprocessed")
    def unprocess(modeladmin, request, queryset):
        queryset.update(processed=False)


@admin.register(VehicleSession)
class VehicleSessionAdmin(PrettyJsonAdmin, admin.ModelAdmin):
    readonly_fields = ("formatted_route_points", "formatted_state", "created_at")
    exclude = ("merged_state", "route_points")
    list_display = (
        "vehicle",
        "activity_type",
        "started_at",
        "ended_at",
        "total_distance_km",
        "electric_distance_km",
        "petrol_distance_km",
        "distance_split_method",
        "fuel_level_start_liters",
        "fuel_level_end_liters",
        "fuel_level_change_display",
        "created_at",
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        energy_field = form.base_fields.get("electric_consumed_kwh")

        if energy_field:
            energy_field.label = (
                "Electric charged kWh"
                if obj and obj.activity_type == VehicleSession.ActivityType.CHARGE
                else "Electric consumed kWh"
            )
        return form

    @admin.display(description="Split source")
    def distance_split_method(self, obj):
        return obj.get_distance_split_source_display() or "-"

    @admin.display(description="Fuel level change (L)")
    def fuel_level_change_display(self, obj):
        return obj.fuel_level_change_liters

    @admin.display(description="Meged State")
    def formatted_state(self, obj):
        return self.format_json(obj, "merged_state")

    @admin.display(description="Route Points")
    def formatted_route_points(self, obj):
        return self.format_json(obj, "route_points")

    def delete_model(self, request, obj):
        BMWCarDataEvent.objects.filter(session_id=obj.id).update(processed=False)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        BMWCarDataEvent.objects.filter(session_id__in=queryset).update(processed=False)
        super().delete_queryset(request, queryset)
