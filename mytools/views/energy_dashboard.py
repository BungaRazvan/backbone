import datetime

from django.views import View
from django.utils.decorators import method_decorator
from django.http.response import JsonResponse
from django.db.models import (
    Sum,
    OuterRef,
    Subquery,
    F,
    FloatField,
    ExpressionWrapper,
    DurationField,
    DecimalField,
)
from django.db.models.functions import Coalesce, Round, ExtractDay, Cast

from rest_framework import serializers

from common.auth.decorators import require_token
from mytools.models import InverterDataPoint, TariffPeriod

MICROSECONDS_IN_A_DAY = 86400000000


class EnergyStatsDashboardSerializer(serializers.Serializer):
    lifetime_charge = serializers.FloatField()
    lifetime_discharge = serializers.FloatField()
    lifetime_home_consumption = serializers.FloatField()
    lifetime_import = serializers.FloatField()
    lifetime_export = serializers.FloatField()
    total_theoretical_cost = serializers.FloatField()
    total_exported_revenue = serializers.FloatField()
    total_standing_charge = serializers.FloatField()
    total_actual_cost = serializers.FloatField()
    lifetime_savings = serializers.FloatField()
    rte_percentage = serializers.SerializerMethodField()

    def get_rte_percentage(self, obj):
        charge = obj.get("lifetime_charge") or 0.0
        discharge = obj.get("lifetime_discharge") or 0.0

        return round((discharge / charge * 100), 2) if charge > 0 else 100.0


class EnergyStatsDashboard(View):
    http_method_names = ["get"]

    @method_decorator(require_token(app_name="mytools"))
    def get(self, request):

        totals = InverterDataPoint.objects.aggregate(
            lifetime_charge=Sum("idp_battery_charge_kwh"),
            lifetime_discharge=Sum("idp_battery_discharge_kwh"),
            lifetime_home_consumption=Sum("idp_home_consumption_kwh"),
            lifetime_import=Sum("idp_grid_import_kwh"),
            lifetime_export=Sum("idp_grid_export_kwh"),
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

        energy_stats_queryset = InverterDataPoint.objects.annotate(
            raw_import_rate=Subquery(tariff_import_subquery, output_field=FloatField()),
            raw_export_rate=Subquery(tariff_export_subquery, output_field=FloatField()),
        ).annotate(
            import_rate=Coalesce(F("raw_import_rate"), 0.24, output_field=FloatField()),
            export_rate=Coalesce(F("raw_export_rate"), 0.0, output_field=FloatField()),
        )

        calculated_queryset = energy_stats_queryset.annotate(
            theoretical_cost=ExpressionWrapper(
                F("idp_home_consumption_kwh") * F("import_rate"),
                output_field=FloatField(),
            ),
            actual_cost=ExpressionWrapper(
                F("idp_grid_import_kwh") * F("import_rate"), output_field=FloatField()
            ),
            exported_revenue=ExpressionWrapper(
                F("idp_grid_export_kwh") * F("export_rate"), output_field=FloatField()
            ),
        ).annotate(
            total_savings_gbp=ExpressionWrapper(
                F("theoretical_cost") - F("actual_cost"), output_field=FloatField()
            )
        )

        energy_stats = calculated_queryset.aggregate(
            total_theoretical_cost=Coalesce(
                Sum("theoretical_cost"), 0.0, output_field=FloatField()
            ),
            total_exported_revenue=Coalesce(
                Sum("exported_revenue"), 0.0, output_field=FloatField()
            ),
            total_actual_cost=Coalesce(
                Sum("actual_cost"), 0.0, output_field=FloatField()
            ),
            lifetime_savings=Coalesce(
                Round(Sum("total_savings_gbp"), 2), 0.0, output_field=FloatField()
            ),
        )

        end_date_or_today = Coalesce(F("tp_end_date"), datetime.date.today())

        duration_expr = ExpressionWrapper(
            end_date_or_today - F("tp_start_date"), output_field=DurationField()
        )

        standing_rates = (
            TariffPeriod.objects.filter(
                tp_standing_charge_rate__gt=0, tp_start_date__lte=datetime.date.today()
            )
            .annotate(duration_ms=duration_expr)
            .annotate(
                days=ExpressionWrapper(
                    F("duration_ms") / MICROSECONDS_IN_A_DAY,
                    output_field=DecimalField(),
                )
            )
            .annotate(standing_charge=F("days") * F("tp_standing_charge_rate"))
            .aggregate(total_standing_charge=Sum("standing_charge"))
        )

        combined_data = {**totals, **energy_stats, **standing_rates}
        serializer = EnergyStatsDashboardSerializer(combined_data)
        return JsonResponse(safe=False, data=serializer.data)
