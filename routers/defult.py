from .base import BaseRouter


class DefaultRouter(BaseRouter):
    route_app_labels = {"auth", "contenttypes", "sessions", "admin"}
    db_name = "default"
