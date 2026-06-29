from django.urls import path
from .views import EfsListView, EfsEventsListView, EtfsDashboard

urlpatterns = [
    path("etfs-list", EfsListView.as_view()),
    path("etfs-events", EfsEventsListView.as_view()),
    path("etfs-dashboard", EtfsDashboard.as_view()),
]
