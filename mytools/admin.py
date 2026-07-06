import os

from decimal import Decimal

from django.contrib import admin
from django.forms.models import model_to_dict
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from mytools.services.parse_bill import BillParseService, BillParseParameters

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
    list_display = ("b_provider", "b_gross_cost", "b_date")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.b_file:
            service = BillParseService()
            args = BillParseParameters(file_path=obj.b_file.path)
            sections = service.extract_sections(obj.b_provider, args)
            gross_cost = Decimal("0.00")
            total_cost = Decimal("0.00")

            if not sections.values():
                return

            for result in sections.values():
                model = result.to_model()
                model_class, prefix = result.model_mappings()
                bill_attr = f"{prefix}bill"

                if model is None:
                    continue

                instance_as_dict = model_to_dict(model)
                instance_as_dict.pop(bill_attr, None)

                model_class.objects.update_or_create(
                    **{bill_attr: obj}, defaults=instance_as_dict
                )

                total_cost += Decimal(result.total_cost)

                if not isinstance(model, Seg):
                    gross_cost += Decimal(result.total_cost)

            file_path = obj.b_file.path
            obj.b_gross_cost = gross_cost
            obj.b_total_cost = total_cost
            obj.b_date = service.extract_date(obj.b_provider, args)
            obj.b_file.delete(save=True)

            if os.path.exists(file_path):
                os.remove(file_path)
