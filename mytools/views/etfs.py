from datetime import timezone, datetime

from django.views import View
from django.http.response import JsonResponse
from django.db.models import Prefetch, Q, Min

from common.utils import require_token
from mytools.models import Etf, EtfShare, EtfEvent
from rest_framework import serializers


class ShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtfShare
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtfEvent
        fields = [
            "ee_id",
            "ee_etf",
            "ee_ex_date",
            "ee_payment_date",
            "ee_ex_estimated",
            "ee_payment_estimated",
            "ee_pay_per_share",
            "ee_eligible_shares_amount",
        ]


class EtfSerializer(serializers.ModelSerializer):
    shares = ShareSerializer(many=True, read_only=True)
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Etf
        fields = "__all__"


class EfsListView(View):
    http_method_names = ["get"]

    @require_token("mytools")
    def get(self, request):

        today = datetime.now(timezone.utc).now().date()

        future_events = Prefetch(
            "events",
            queryset=EtfEvent.objects.filter(ee_ex_date__gte=today).order_by(
                "ee_ex_date"
            ),
        )
        etfs = (
            Etf.objects.all()
            .prefetch_related(future_events, "shares")
            .annotate(
                next_dividend_date=Min(
                    "events__ee_ex_date", filter=Q(events__ee_ex_date__gte=today)
                )
            )
        )
        data = EtfSerializer(etfs, many=True).data

        return JsonResponse(data, safe=False)
