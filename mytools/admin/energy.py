from django.contrib import admin

# Register your models here.
from mytools.models import (
    InverterDataPoint,
    ChargePointHistory,
)


@admin.register(InverterDataPoint)
class InverterDataPointAdmin(admin.ModelAdmin):
    list_display = (
        "idp_date",
        "idp_solar_generation_kwh",
        "idp_grid_export_kwh",
        "idp_grid_import_kwh",
        "idp_home_consumption_kwh",
        "idp_battery_charge_kwh",
        "idp_battery_discharge_kwh",
    )

    list_display_links = ("idp_date",)

    ordering = ("-idp_date",)


@admin.register(ChargePointHistory)
class ChargePointHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "cph_kwh",
        "cph_net_cost",
        "cph_gross_cost",
        "cph_started_at",
        "cph_completed_at",
        "cph_feed_in_loss",
        "cph_battery_kwh",
    )
    ordering = ("-cph_completed_at",)
