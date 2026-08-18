from django.urls import path
from .views import (
    EfsListView,
    EfsEventsListView,
    EtfsDashboard,
    SolarStatsView,
    BillsStatsView,
    BMWCarDataAuthDeviceCodeView,
    BMWCarDataAuthTokenView,
    BMWCarDataContainersView,
    BMWTelematicView,
)

urlpatterns = [
    path("etfs-list", EfsListView.as_view()),
    path("etfs-events", EfsEventsListView.as_view()),
    path("etfs-dashboard", EtfsDashboard.as_view()),
    path("solar-stats", SolarStatsView.as_view()),
    path("bills-stats", BillsStatsView.as_view()),
    path("bmw/cardata/auth-device", BMWCarDataAuthDeviceCodeView.as_view()),
    path("bmw/cardata/auth-token", BMWCarDataAuthTokenView.as_view()),
    path("bmw/cardata/containers", BMWCarDataContainersView.as_view()),
    path("bmw/cardata/telematics", BMWTelematicView.as_view()),
]
