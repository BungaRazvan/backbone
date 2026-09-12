import dataclasses

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils.decorators import method_decorator

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from common.auth.decorators import require_token, validate_arguments
from mytools.models import InverterDataPoint


@dataclasses.dataclass
class Args:
    statsYear: int


class SolarGenerationSerializer(serializers.Serializer):
    month = serializers.DateField(format="%b")
    generated_energy = serializers.FloatField()
    consumed_energy = serializers.FloatField()


class SolarGenerationView(APIView):
    @method_decorator([require_token(app_name="mytools"), validate_arguments(Args)])
    def get(self, request, args: Args):
        data_points = InverterDataPoint.objects.filter(
            idp_date__year=args.statsYear
        ).annotate(month=TruncMonth("idp_date"))
        data_points = (
            data_points.values("month")
            .annotate(
                generated_energy=Sum("idp_solar_generation_kwh"),
                consumed_energy=Sum("idp_home_consumption_kwh"),
            )
            .order_by("month")
        )

        serializer = SolarGenerationSerializer(data_points, many=True)
        return Response(serializer.data)
