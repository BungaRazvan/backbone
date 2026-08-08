import os

from django.contrib import admin

from decimal import Decimal
from django.forms.models import model_to_dict
from mytools.services.parse_bill import BillParseService
from mytools.services.parse_bill.parameters import BillParseParameters

from mytools.models import (
    TariffPeriod,
    Bill,
    Gas,
    Seg,
    Electricity,
)


@admin.register(TariffPeriod)
class TariffPeriodAdmin(admin.ModelAdmin):
    list_display = ("tp_tariff_name", "tp_provider_name")


class ElectricityInline(admin.StackedInline):
    model = Electricity
    can_delete = False
    extra = 0


class GasInline(admin.StackedInline):
    model = Gas
    can_delete = False
    extra = 0


class SegInline(admin.StackedInline):
    model = Seg
    can_delete = False
    extra = 0


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
            net_cost = Decimal("0.00")

            if not sections.values():
                return

            items = [result for sections in sections.values() for result in sections]

            for result in items:
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

                net_cost += Decimal(result.total_cost)

                if not isinstance(model, Seg):
                    gross_cost += Decimal(result.total_cost)

            file_path = obj.b_file.path
            obj.b_gross_cost = gross_cost
            obj.b_net_cost = net_cost
            obj.b_date = service.extract_date(obj.b_provider, args)
            obj.b_file.delete(save=True)

            if os.path.exists(file_path):
                os.remove(file_path)
