from typing import Optional

from celery import shared_task

from mytools.models import (
    ElectricityBill,
    SegBill,
    InverterDataPoint,
    AnnualEnergySummary,
    TariffPeriod,
)
from datetime import date

from django.db.models import OuterRef, Subquery, DecimalField, F, ExpressionWrapper
from django.db.models.functions import Coalesce


@shared_task
def calculate_yearly_electric_usage(year: Optional[int] = None):

    if year is None:
        year = date.today().year

    annual_summary = (
        AnnualEnergySummary.objects.filter(
            last_proccessed_month__gte=0, year__lte=year, last_proccessed_month__lte=12
        )
        .order_by("year")
        .first()
    )

    if annual_summary is None:
        annual_summary = AnnualEnergySummary(year=year)

    year = annual_summary.year
    month = annual_summary.last_proccessed_month + 1

    inverter_data = InverterDataPoint.objects.filter(
        idp_date__month__gte=month, idp_date__year=year
    )

    tariff_subquery = TariffPeriod.objects.filter(
        tp_start_date__lte=OuterRef("idp_date"),
        tp_end_date__gte=OuterRef("idp_date"),
    )

    tariff_import_subquery = tariff_subquery.filter(
        tp_standard_import_rate__gt=0,
    ).values("tp_standard_import_rate")[:1]

    home_data = inverter_data.annotate(
        import_rate=Coalesce(
            Subquery(tariff_import_subquery), 0.24, output_field=DecimalField()
        )
    ).annotate(
        gross_cost=ExpressionWrapper(
            F("idp_home_consumption_kwh") * F("import_rate"),
            output_field=DecimalField(),
        )
    )

    electric_bills = ElectricityBill.objects.filter(
        e_from_date__month__gte=month,
        e_from_date__year=year,
    ).order_by("e_from_date")

    seg_bills = SegBill.objects.filter(
        s_from_date__month__gte=month,
        s_from_date__year=year,
    ).order_by("s_from_date")

    for electric_bill in electric_bills:
        annual_summary.grid_import_kwh += electric_bill.e_kwh_used
        annual_summary.total_net_cost += electric_bill.pure_energy_cost
        annual_summary.last_proccessed_month = electric_bill.e_from_date.month

    for seg_bill in seg_bills:
        annual_summary.grid_export_kwh += seg_bill.s_kwh_used
        annual_summary.total_exported_revenue += abs(seg_bill.s_total_cost)

    for data in home_data:
        annual_summary.home_consumption_kwh += data.idp_home_consumption_kwh
        annual_summary.total_gross_cost += data.gross_cost

    annual_summary.savings = (
        annual_summary.total_gross_cost - annual_summary.total_net_cost
    )
    annual_summary.save()
