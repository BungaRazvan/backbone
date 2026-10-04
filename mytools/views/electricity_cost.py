from decimal import Decimal

from django.db.models.functions import Coalesce
from django.db.models import F, ExpressionWrapper, Subquery, DecimalField, OuterRef, Sum
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from common.auth.backends import app_auth
from common.auth.decorators import validate_arguments
from mytools.models import (
    Electricity,
    BillingCycle,
    Seg,
    TariffPeriod,
    InverterDataPoint,
)
from django.utils.decorators import method_decorator

import dataclasses
import datetime
from collections import defaultdict

from mytools.services.parse_bill.parameters import UtilityCategory
from .solar.solar_performance import get_month_range_for_billing_cycle


class ElectricitySerializer(serializers.Serializer):

    grid_import = serializers.FloatField()
    grid_export = serializers.FloatField()
    total_exported_revenue = serializers.FloatField()
    savings = serializers.FloatField()
    total_net_cost = serializers.FloatField()


@dataclasses.dataclass
class Args:
    statsPeriod: int


class ElectricityCostView(APIView):

    authentication_classes = [app_auth("mytools")]

    @method_decorator(validate_arguments(Args))
    def get(self, request, args):
        year = datetime.datetime.now().year
        month = args.statsPeriod

        billing_cycle = (
            BillingCycle.objects.covering_year(
                datetime.date.today().year,
                cycle_type="monthly",
                category=UtilityCategory.ELECTRICITY.value,
            )
            .order_by("-end_date")
            .first()
        )

        if billing_cycle is None:
            return Response(
                {"error": "No billing cycle found for the specified period."},
                status=404,
            )

        data = defaultdict(Decimal)
        start_date, end_date = get_month_range_for_billing_cycle(
            year, month, billing_cycle.cycle_day
        )
        electrict_bills = Electricity.objects.filter(
            e_from_date__gte=start_date, e_to_date__lte=end_date
        )

        seg_bills = Seg.objects.filter(
            s_from_date__gte=start_date, s_to_date__lte=end_date
        )

        if not electrict_bills.exists():
            return Response(
                {"error": "No electricity bills found for the specified period."},
                status=404,
            )

        tariff_subquery = TariffPeriod.objects.filter(
            tp_start_date__lte=OuterRef("idp_date"),
            tp_end_date__gte=OuterRef("idp_date"),
        )

        tariff_import_subquery = tariff_subquery.filter(
            tp_standard_import_rate__gt=0,
        ).values("tp_standard_import_rate")[:1]

        energy_stats_queryset = (
            InverterDataPoint.objects.filter(
                idp_date__gte=start_date, idp_date__lte=end_date
            )
            .annotate(
                raw_import_rate=Subquery(
                    tariff_import_subquery, output_field=DecimalField()
                ),
            )
            .annotate(
                import_rate=Coalesce(
                    F("raw_import_rate"), 0.24, output_field=DecimalField()
                ),
                gross_cost=ExpressionWrapper(
                    F("idp_home_consumption_kwh") * F("import_rate"),
                    output_field=DecimalField(),
                ),
            )
        ).aggregate(
            total_gross_cost=Coalesce(Sum("gross_cost"), 0, output_field=DecimalField())
        )

        for electric_bill in electrict_bills:
            data["grid_import"] += electric_bill.e_kwh_used
            data["total_net_cost"] += electric_bill.pure_energy_cost

        for seg_bill in seg_bills:
            data["grid_export"] += seg_bill.s_kwh_used
            data["total_exported_revenue"] += abs(seg_bill.s_total_cost)

        data["savings"] = (
            energy_stats_queryset["total_gross_cost"] - data["total_net_cost"]
        )
        serializer = ElectricitySerializer(data)

        return Response(serializer.data)
