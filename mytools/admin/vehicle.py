from mytools.models import VehicleTrip, VehicleTelemetryLog, Vehicle
from django.contrib import admin


@admin.register(VehicleTrip)
class VehicleTripAdmin(admin.ModelAdmin):
    list_display = ("vt_distance_miles", "vt_electric_miles", "vt_fuel_miles")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("v_name", "v_make", "v_year")


@admin.register(VehicleTelemetryLog)
class VehicleTelemetryLogAdmin(admin.ModelAdmin):
    list_display = (
        "vtl_odometer_km",
        "vtl_remaining_electric_range_km",
        "vtl_latitude",
        "vtl_longitude",
    )
