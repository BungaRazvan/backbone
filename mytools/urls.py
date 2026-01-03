from django.urls import path
from .views import EfsListView


urlpatterns = [path("list-etfs", EfsListView.as_view())]
