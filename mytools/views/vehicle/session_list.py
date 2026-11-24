import dataclasses

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response


from common.auth.decorators import validate_arguments
from common.auth.backends import app_auth

from django.utils.decorators import method_decorator
from mytools.models import VehicleSession


class VehicleSessionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleSession

        fields = [
            "id",
            "vehicle_id",
            "activity_type",
            "started_at",
            "ended_at",
            "start_odometer_km",
            "end_odometer_km",
        ]


class VehiceSessionListView(APIView):

    authentication_classes = [app_auth("mytools")]

    def get(self, request):
        qs = VehicleSession.objects.filter(
            activity_type__in=[
                VehicleSession.ActivityType.DRIVE,
                # VehicleSession.ActivityType.CHARGE,
            ],
        ).order_by("-started_at")

        serializer = VehicleSessionListSerializer(qs, many=True)

        return Response(serializer.data)
