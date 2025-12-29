from .base import BaseRouter


class MyToolsRouter(BaseRouter):
    route_app_labels = {"mytools"}
    db_name = "mytools_db"
