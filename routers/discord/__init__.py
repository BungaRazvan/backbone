from routers.base import BaseRouter


class DiscordRouter(BaseRouter):
    route_app_labels = {'discord'}
    db_name = 'discord_db'
