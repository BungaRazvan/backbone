from django.urls import path
from .views import (
    EfsListView,
    EfsEventsListView,
    EtfsDashboard,
    SolarStatsView,
    BillsStatsView,
)

urlpatterns = [
    path("etfs-list", EfsListView.as_view()),
    path("etfs-events", EfsEventsListView.as_view()),
    path("etfs-dashboard", EtfsDashboard.as_view()),
    path("solar-stats", SolarStatsView.as_view()),
    path("bills-stats", BillsStatsView.as_view()),
]
