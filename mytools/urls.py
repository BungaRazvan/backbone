from django.urls import path

from mytools.views.solar.solar_performance import SolarPerformanceView
from .views import (
    EfsListView,
    EfsEventsListView,
    EtfsMetrics,
    SolarPerformanceView,
    SolarGenerationView,
    BillsStatsView,
)

urlpatterns = [
    path("etfs/list", EfsListView.as_view()),
    path("etfs/events", EfsEventsListView.as_view()),
    path("etfs/metrics", EtfsMetrics.as_view()),
    path("solar/performance", SolarPerformanceView.as_view()),
    path("solar/generation", SolarGenerationView.as_view()),
    path("bills-stats", BillsStatsView.as_view()),
]
