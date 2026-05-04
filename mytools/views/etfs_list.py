from datetime import timezone, datetime

from django.views import View
from django.http.response import JsonResponse
from django.db.models import Prefetch

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
    future_event = serializers.SerializerMethodField()
    recent_event = serializers.SerializerMethodField()

    class Meta:
        model = Etf
        fields = "__all__"

    def get_future_event(self, obj):

        events = getattr(obj, "future_events", [])

        if events:
            return EventSerializer(events[0]).data

        return None

    def get_recent_event(self, obj):

        events = getattr(obj, "recent_events", [])

        if events:
            return EventSerializer(events[0]).data

        return None


class EfsListView(View):
    http_method_names = ["get"]

    @require_token("mytools")
    def get(self, request):

        today = datetime.now(timezone.utc).now().date()

        future_events = Prefetch(
            "events",
            queryset=EtfEvent.objects.filter(ee_ex_date__gt=today).order_by(
                "ee_ex_date"
            ),
            to_attr="future_events",
        )

        recent_events = Prefetch(
            "events",
            queryset=EtfEvent.objects.filter(ee_ex_date__lte=today).order_by(
                "-ee_ex_date"
            ),
            to_attr="recent_events",
        )

        etfs = Etf.objects.all().prefetch_related(
            future_events, recent_events, "shares"
        )
        data = EtfSerializer(etfs, many=True).data

        return JsonResponse(data, safe=False)
