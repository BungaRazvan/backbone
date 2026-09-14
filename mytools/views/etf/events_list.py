from datetime import timezone, datetime
from rest_framework.views import APIView
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator
from django.db.models import Q
import dataclasses
from common.auth.decorators import require_token, validate_arguments
from mytools.models import Etf, EtfEvent
from rest_framework import serializers


class EtfSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etf
        fields = ["ef_name"]


class EventSerializer(serializers.ModelSerializer):
    ee_etf = EtfSerializer(required=False)

    class Meta:
        model = EtfEvent
        fields = [
            "ee_ex_date",
            "ee_etf",
            "ee_payment_date",
            "ee_ex_estimated",
            "ee_payment_estimated",
            "ee_eligible_shares_amount",
        ]


@dataclasses.dataclass
class Args:
    start_date: datetime
    end_date: datetime


class EfsEventsListView(APIView):

    @method_decorator([require_token(app_name=("mytools")), validate_arguments(Args)])
    def get(
        self,
        request,
        args: Args,
    ):

        events = (
            EtfEvent.objects.filter(
                Q(ee_ex_date__gte=args.start_date) & Q(ee_ex_date__lte=args.end_date)
            )
            .select_related("ee_etf")
            .order_by("ee_ex_date", "ee_payment_date")
        )

        data = EventSerializer(events, many=True).data

        return JsonResponse(data, safe=False)
