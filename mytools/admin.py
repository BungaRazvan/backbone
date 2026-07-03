from django.contrib import admin
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from mytools.services.parse_bill.edf_energy import parse_bill

# Register your models here.
from mytools.models import (
    EtfShare,
    Etf,
    EtfEvent,
    InverterDataPoint,
    TariffPeriod,
    Bill,
    Gas,
    Seg,
    Electricity,
)


class EtfShareInline(admin.StackedInline):
    ordering = ("-efs_purchase_date",)
    readonly_fields = ("efs_created_on",)
    model = EtfShare
    extra = 0


class EtfEventInline(admin.StackedInline):
    ordering = ("-ee_ex_date",)
    readonly_fields = ("ee_created_on",)
    model = EtfEvent
    extra = 0


@admin.register(Etf)
class EtfAdmin(admin.ModelAdmin):
    inlines = [EtfShareInline, EtfEventInline]


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


@admin.register(TariffPeriod)
class TariffPeriodAdmin(admin.ModelAdmin):
    list_display = ("tp_tariff_name", "tp_provider_name")


class ElectricityInline(admin.StackedInline):
    model = Electricity
    can_delete = False


class GasInline(admin.StackedInline):
    model = Gas
    can_delete = False


class SegInline(admin.StackedInline):
    model = Seg
    can_delete = False


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    inlines = [ElectricityInline, GasInline, SegInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.b_file:
            data = parse_bill(obj.b_file.path)
            obj.b_from_period = data.get("electricity", {}).get("from_date")
            obj.b_to_period = data.get("electricity", {}).get("to_date")
            obj.b_total_amount_due = data.get("net_total_amount_due")
            obj.save()

            if all(data.get("electricity", {}).values()):
                json_data = data.get("electricity", {})
                Electricity.objects.update_or_create(
                    e_bill=obj,
                    defaults={
                        "e_kwh_used": json_data.get("usage_kwh"),
                        "e_standing_charge_total": json_data.get(
                            "standing_charge_total"
                        ),
                        "e_standing_charge_rate": json_data.get("standing_charge_rate"),
                        "e_total_cost": json_data.get("section_total"),
                        "e_unit_rate": json_data.get("unit_rate_p_kwh"),
                    },
                )

                if all(data.get("gas", {}).values()):
                    json_data = data.get("gas", {})
                    Gas.objects.update_or_create(
                        g_bill=obj,
                        defaults={
                            "g_kwh_used": json_data.get("usage_kwh"),
                            "g_standing_charge_total": json_data.get(
                                "standing_charge_total"
                            ),
                            "g_standing_charge_rate": json_data.get(
                                "standing_charge_rate"
                            ),
                            "g_total_cost": json_data.get("section_total"),
                            "g_unit_rate": json_data.get("unit_rate_p_kwh"),
                        },
                    )
