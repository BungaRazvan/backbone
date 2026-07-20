import dataclasses

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from common.auth.decorators import require_token, validate_arguments
from mytools.models import Bill, Electricity, Gas, Seg
from django.utils.decorators import method_decorator
from django.db.models import OuterRef, Subquery, Sum, Value, DecimalField
from django.db.models.functions import Coalesce


class ElectricitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Electricity
        fields = "__all__"


class BillStatsSerializer(serializers.ModelSerializer):
    month = serializers.SerializerMethodField()
    costs = serializers.SerializerMethodField()
    usage_kwh = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = ("month", "b_date", "b_provider", "costs", "usage_kwh")

    def get_month(self, obj):
        # Returns formatted string like "Jun 2026"
        return obj.b_date.strftime("%b %Y") if obj.b_date else ""

    def get_costs(self, obj):
        elec_cost = obj.electricity.aggregate(total=Sum("e_total_cost"))["total"] or 0.0
        gas_cost = obj.gas.aggregate(total=Sum("g_total_cost"))["total"] or 0.0
        seg_credit = obj.seg.aggregate(total=Sum("s_total_cost"))["total"] or 0.0

        return {
            "electricity": float(elec_cost),
            "gas": float(gas_cost),
            "seg": float(seg_credit),
        }

    def get_usage_kwh(self, obj):
        elec_kwh = obj.electricity.aggregate(total=Sum("e_kwh_used"))["total"] or 0.0
        gas_kwh = obj.gas.aggregate(total=Sum("g_kwh_used"))["total"] or 0.0
        seg_kwh = obj.seg.aggregate(total=Sum("s_kwh_used"))["total"] or 0.0

        return {
            "electricity": float(elec_kwh),
            "gas": float(gas_kwh),
            "seg": float(seg_kwh),
        }


@dataclasses.dataclass
class BillArgs:
    pass


class BillsStatsView(APIView):
    @method_decorator([require_token(app_name="mytools"), validate_arguments(BillArgs)])
    def get(self, request, args):

        elec_subquery = (
            Electricity.objects.filter(
                e_bill=OuterRef("pk"), e_from_date__month=OuterRef("b_date__month")
            )
            .values("e_bill")
            .annotate(total=Sum("e_total_cost"))
            .values("total")
        )

        gas_subquery = (
            Gas.objects.filter(
                g_bill=OuterRef("pk"), g_from_date__month=OuterRef("b_date__month")
            )
            .values("g_bill")
            .annotate(total=Sum("g_total_cost"))
            .values("total")
        )

        seg_subquery = (
            Seg.objects.filter(
                s_bill=OuterRef("pk"), s_from_date__month=OuterRef("b_date__month")
            )
            .values("s_bill")
            .annotate(total=Sum("s_total_cost"))
            .values("total")
        )

        # Main Query
        data = Bill.objects.annotate(
            elec_cost=Coalesce(
                Subquery(elec_subquery), Value(0.0), output_field=DecimalField()
            ),
            gas_cost=Coalesce(
                Subquery(gas_subquery), Value(0.0), output_field=DecimalField()
            ),
            seg_cost=Coalesce(
                Subquery(seg_subquery), Value(0.0), output_field=DecimalField()
            ),
        ).order_by("-b_date")

        # data = (
        #     Bill.objects.all()
        #     .prefetch_related("electricity", "gas", "seg")
        #     .filter(electricity__e_from_date__month=OuterRef("b_date__month"))
        #     .order_by("-b_date")
        # )

        serializer = BillStatsSerializer(data, many=True)
        return Response(serializer.data)
