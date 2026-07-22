import dataclasses


from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from common.auth.decorators import require_token, validate_arguments
from mytools.models import Bill, Electricity, Gas, Seg
from django.utils.decorators import method_decorator
from django.db.models import Prefetch, F, Sum


class BillStatsSerializer(serializers.ModelSerializer):
    month = serializers.SerializerMethodField()
    costs = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = ("month", "b_date", "b_provider", "costs", "usage")

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

    def get_usage(self, obj):
        elec_kwh = obj.electricity.aggregate(total=Sum("e_kwh_used"))["total"] or 0.0
        gas_kwh = obj.gas.aggregate(total=Sum("g_kwh_used"))["total"] or 0.0
        seg_kwh = obj.seg.aggregate(total=Sum("s_kwh_used"))["total"] or 0.0

        return {
            "electricity": float(elec_kwh),
            "gas": float(gas_kwh),
            "seg": float(seg_kwh),
        }


class BillsStatsView(APIView):
    @method_decorator([require_token(app_name="mytools")])
    def get(self, request, args):

        data = (
            Bill.objects.all()
            .prefetch_related(
                Prefetch(
                    "electricity",
                    queryset=Electricity.objects.filter(
                        e_to_date__month=F("e_bill__b_date__month")
                    ),
                ),
                Prefetch(
                    "gas",
                    queryset=Gas.objects.filter(
                        g_to_date__month=F("g_bill__b_date__month")
                    ),
                ),
                Prefetch(
                    "seg",
                    queryset=Seg.objects.filter(
                        s_to_date__month=F("s_bill__b_date__month")
                    ),
                ),
            )
            .order_by("b_date")
        )
        serializer = BillStatsSerializer(data, many=True)
        return Response(serializer.data)
