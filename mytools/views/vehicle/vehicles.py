import dataclasses

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response


from common.auth.decorators import validate_arguments
from common.auth.backends import app_auth

from django.utils.decorators import method_decorator
from mytools.models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle


class VehicleListView(APIView):
    authentication_classes = [app_auth("mytools")]

    def get(self, request):

        vehicles = Vehicle.objects.all()

        serializers = VehicleSerializer(vehicles, many=True)

        return APIView(serializers.data)
