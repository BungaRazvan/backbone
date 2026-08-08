import datetime
import calendar

from decimal import Decimal

from rest_framework.views import APIView
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator
from django.db.models import Sum, Q, F, OuterRef, Subquery
from django.db.models.functions import Coalesce

from rest_framework import serializers

from common.auth.decorators import require_token
from mytools.models import EtfShare, EtfEvent


class EtfsDashboardSerializer(serializers.Serializer):
    out_of_pocket = serializers.DecimalField(max_digits=20, decimal_places=8)
    compounding_cost = serializers.DecimalField(max_digits=20, decimal_places=8)
    cumulative_dividends = serializers.DecimalField(max_digits=20, decimal_places=8)
    dividends_this_month = serializers.DecimalField(max_digits=20, decimal_places=8)
    invested = serializers.SerializerMethodField()
    dividend_roi = serializers.SerializerMethodField()

    def get_invested(self, obj):

        out_of_pocket = obj.get("out_of_pocket") or 0
        compounding_cost = obj.get("compounding_cost") or 0

        return out_of_pocket + compounding_cost

    def get_dividend_roi(self, obj):
        out_of_pocket = float(obj.get("out_of_pocket") or 0)
        cumulative_dividends = float(obj.get("cumulative_dividends") or 0)

        if out_of_pocket == 0:
            return 0.0

        roi = (cumulative_dividends / out_of_pocket) * 100
        return round(roi, 2)


class EtfsDashboard(APIView):

    @method_decorator(require_token(app_name=("mytools")))
    def get(self, request):
        today = datetime.date.today()
        _, last_day_of_month = calendar.monthrange(today.year, today.month)

        shares_stats = EtfShare.objects.aggregate(
            out_of_pocket=Sum(
                "efs_total_price",
                filter=Q(efs_funds=EtfShare.Funds.SALARY) | Q(efs_funds__isnull=True),
            ),
            compounding_cost=Sum(
                "efs_total_price",
                filter=Q(efs_funds=EtfShare.Funds.DIVIDENTS),
            ),
        )

        eligible_shares_subquery = (
            EtfShare.objects.filter(
                efs_ef_id=OuterRef("ee_etf_id"),
                efs_purchase_date__lte=OuterRef("ee_ex_date"),
            )
            .values("efs_ef_id")
            .annotate(total_shares=Sum("efs_amount"))
            .values("total_shares")
        )

        events_stats = EtfEvent.objects.annotate(
            calculated_shares=Coalesce(
                Subquery(eligible_shares_subquery), Decimal("0.0")
            )
        ).aggregate(
            cumulative_dividends=Coalesce(
                Sum(
                    F("calculated_shares") * F("ee_pay_per_share"),
                    filter=Q(ee_payment_date__lte=today),
                ),
                Decimal("0.0"),
            ),
            dividends_this_month=Coalesce(
                Sum(
                    F("calculated_shares") * F("ee_pay_per_share"),
                    filter=Q(
                        ee_ex_date__range=(
                            today.replace(day=1),
                            today.replace(day=last_day_of_month),
                        )
                    ),
                ),
                Decimal("0.0"),
            ),
        )
        combined_data = {**shares_stats, **events_stats}
        serializer = EtfsDashboardSerializer(combined_data)

        return JsonResponse(safe=False, data=serializer.data)
