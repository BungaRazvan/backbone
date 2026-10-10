from typing import Optional

import datetime
import dataclasses

from django.utils.decorators import method_decorator
from django.db.models import (
    Sum,
    OuterRef,
    Subquery,
    F,
    ExpressionWrapper,
    DecimalField,
    Q,
)
from django.db.models.functions import Coalesce, Round

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from common.auth.decorators import require_token, validate_arguments
from mytools.models import InverterDataPoint, TariffPeriod, BillingCycle
from mytools.services.parse_bill.parameters import UtilityCategory


def get_month_range_for_billing_cycle(year: int, month: int, cycle_day: int):
    start_year = year
    start_month = month - 1

    if start_month == 0:
        start_year -= 1
        start_month = 12

    return (
        datetime.date(start_year, start_month, cycle_day),
        datetime.date(year, month, cycle_day),
    )


class SolarStatsSerializer(serializers.Serializer):
    battery_charge = serializers.FloatField()
    battery_discharge = serializers.FloatField()
    home_consumption = serializers.FloatField()
    grid_import = serializers.FloatField()
    grid_export = serializers.FloatField()
    total_gross_cost = serializers.FloatField()
    total_exported_revenue = serializers.FloatField()
    total_net_cost = serializers.FloatField()
    savings = serializers.FloatField()
    rte_percentage = serializers.SerializerMethodField()

    def get_rte_percentage(self, obj):
        charge = obj.get("battery_charge") or 0.0
        discharge = obj.get("battery_discharge") or 0.0

        if charge <= 0:
            return 0.0

        return round((discharge / charge * 100), 2) if charge > 0 else 100.0


@dataclasses.dataclass
class Args:
    statsPeriodType: Optional[str] = None
    statsPeriod: Optional[int] = None


class SolarPerformanceView(APIView):

    @method_decorator([require_token(app_name="mytools"), validate_arguments(Args)])
    def get(self, request, args: Args):

        totals = InverterDataPoint.objects.all()
        energy_stats_queryset = InverterDataPoint.objects.all()

        if args.statsPeriodType == "month" and args.statsPeriod:
            billing_cycle = (
                BillingCycle.objects.covering_year(
                    datetime.date.today().year,
                    cycle_type="monthly",
                    category=UtilityCategory.ELECTRICITY.value,
                )
                .order_by("-end_date")
                .first()
            )

            filters = Q(idp_date__year=datetime.date.today().year)

            if billing_cycle:
                start_date, end_date = get_month_range_for_billing_cycle(
                    datetime.date.today().year,
                    args.statsPeriod,
                    billing_cycle.cycle_day,
                )

                filters = Q(idp_date__gte=start_date, idp_date__lte=end_date)
            else:
                filters &= Q(idp_date__month=args.statsPeriod)

            totals = totals.filter(filters)
            energy_stats_queryset = energy_stats_queryset.filter(filters)
        elif args.statsPeriodType == "year" and args.statsPeriod:
            totals = totals.filter(idp_date__year=args.statsPeriod)
            energy_stats_queryset = energy_stats_queryset.filter(
                idp_date__year=args.statsPeriod
            )

        totals = totals.aggregate(
            battery_charge=Sum(
                "idp_battery_charge_kwh", output_field=DecimalField()
            ),
            battery_discharge=Sum(
                "idp_battery_discharge_kwh", output_field=DecimalField()
            ),
            home_consumption=Sum(
                "idp_home_consumption_kwh", output_field=DecimalField()
            ),
            grid_import=Sum("idp_grid_import_kwh", output_field=DecimalField()),
            grid_export=Sum("idp_grid_export_kwh", output_field=DecimalField()),
        )

        tariff_subquery = TariffPeriod.objects.filter(
            tp_start_date__lte=OuterRef("idp_date"),
            tp_end_date__gte=OuterRef("idp_date"),
        )

        tariff_import_subquery = tariff_subquery.filter(
            tp_standard_import_rate__gt=0,
        ).values("tp_standard_import_rate")[:1]

        tariff_export_subquery = tariff_subquery.filter(
            tp_standard_export_rate__gt=0,
        ).values("tp_standard_export_rate")[:1]

        energy_stats_queryset = energy_stats_queryset.annotate(
            raw_import_rate=Subquery(
                tariff_import_subquery, output_field=DecimalField()
            ),
            raw_export_rate=Subquery(
                tariff_export_subquery, output_field=DecimalField()
            ),
        ).annotate(
            import_rate=Coalesce(
                F("raw_import_rate"), 0.24, output_field=DecimalField()
            ),
            export_rate=Coalesce(
                F("raw_export_rate"), 0.0, output_field=DecimalField()
            ),
        )

        calculated_queryset = energy_stats_queryset.annotate(
            gross_cost=ExpressionWrapper(
                F("idp_home_consumption_kwh") * F("import_rate"),
                output_field=DecimalField(),
            ),
            net_cost=ExpressionWrapper(
                F("idp_grid_import_kwh") * F("import_rate"), output_field=DecimalField()
            ),
            exported_revenue=ExpressionWrapper(
                F("idp_grid_export_kwh") * F("export_rate"), output_field=DecimalField()
            ),
        ).annotate(
            total_savings_gbp=ExpressionWrapper(
                F("gross_cost") - F("net_cost"), output_field=DecimalField()
            )
        )

        energy_stats = calculated_queryset.aggregate(
            total_gross_cost=Coalesce(
                Sum("gross_cost"), 0.0, output_field=DecimalField()
            ),
            total_exported_revenue=Coalesce(
                Sum("exported_revenue"), 0.0, output_field=DecimalField()
            ),
            total_net_cost=Coalesce(Sum("net_cost"), 0.0, output_field=DecimalField()),
            savings=Coalesce(
                Round(Sum("total_savings_gbp"), 2), 0.0, output_field=DecimalField()
            ),
        )

        combined_data = {**totals, **energy_stats}
        serializer = SolarStatsSerializer(combined_data)

        return Response(serializer.data)
