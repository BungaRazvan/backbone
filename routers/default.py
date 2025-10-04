from .base import BaseRouter


class DefaultRouter(BaseRouter):
    route_app_labels = {"auth", "contenttypes", "sessions", "admin", "common"}
    db_name = "default"
