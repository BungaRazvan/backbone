from django.urls import path

from .views.get_queue_images import GetQueueImages

urlpatterns = [
    path('get-queue-images/', GetQueueImages.as_view())
]
