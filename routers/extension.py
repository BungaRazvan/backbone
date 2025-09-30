from routers.base import BaseRouter


class ExtensionRouter(BaseRouter):
    route_app_labels = {"extension"}
    db_name = "extension_db"
