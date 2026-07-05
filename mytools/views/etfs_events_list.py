from datetime import timezone, datetime
from django.views import View
from django.http.response import JsonResponse
from django.utils.decorators import method_decorator
from django.db.models import Prefetch, Q, Min

from common.auth.decorators import require_token
from mytools.models import Etf, EtfShare, EtfEvent
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


class EfsEventsListView(View):
    http_method_names = ["get"]

    @method_decorator(require_token(app_name=("mytools")))
    def get(self, request):

        today = datetime.now(timezone.utc).now().date()

        events = (
            EtfEvent.objects.filter(
                Q(ee_ex_date__year=today.year) | Q(ee_payment_date__year=today.year)
            )
            .select_related("ee_etf")
            .order_by("ee_ex_date", "ee_payment_date")
        )

        data = EventSerializer(events, many=True).data

        return JsonResponse(data, safe=False)
