from typing import Dict

from rest_framework.views import APIView

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from common.auth.backends import app_auth
from discord.models import MinecraftStat, MinecraftPlayer

import json
from dataclasses import dataclass
from django.utils.decorators import method_decorator
from common.auth.decorators import require_token, validate_arguments


@dataclass
class ArgsPost:
    uuid: str
    stats: Dict
    mc_server_id: str


@dataclass
class ArgsGet:
    quild_id: str


class MinecraftStatsView(APIView):

    @method_decorator([require_token(app_name="discord"), validate_arguments(ArgsPost)])
    def post(self, request, args: ArgsPost):
        uuid = args.uuid
        stats = args.stats
        mc_server_id = args.mc_server_id

        uuid = args.uuid
        stats = args.stats
        mc_server_id = args.mc_server_id

        try:
            player = MinecraftPlayer.objects.get(
                mp_uuid=uuid, mp_mcs_server_id=mc_server_id
            )
        except MinecraftPlayer.DoesNotExist:
            return HttpResponseBadRequest("Unknown Player")

        _, created = MinecraftStat.objects.update_or_create(
            mst_player=player,
            defaults={
                "mst_data": stats,
                "mst_player": player,
            },
        )

        return HttpResponse(status=201 if created else 200)

    @method_decorator([require_token(app_name="discord"), validate_arguments(ArgsGet)])
    def get(self, request, args: ArgsGet):
        ds_quild_id = args.quild_id

        players = MinecraftPlayer.objects.filter(
            mp_ds_quild_id=ds_quild_id
        ).select_related("stat")

        data = []
        for player in players:
            try:
                stat = player.stat
            except MinecraftStat.DoesNotExist:
                continue

            mc_name = player.mp_mc_name
            stats = stat.mst_data

            custom_data = stats.get("stats", {}).get("minecraft:custom", {})
            play_time = calculate_play_time(custom_data)
            deaths = custom_data.get("minecraft:deaths", 0)
            player_kills = custom_data.get("minecraft:player_kills", 0)
            mob_kills = custom_data.get("minecraft:mob_kills", 0)

            data.append(
                {
                    "mc_name": mc_name,
                    "play_time": play_time,
                    "deaths": deaths,
                    "player_kills": player_kills,
                    "mob_kills": mob_kills,
                    "timestamp": stat.mst_timestamp.isoformat(),
                }
            )

        return JsonResponse(data, safe=False)


def calculate_play_time(custom_data):
    ticks = custom_data.get("minecraft:play_time", 0)

    total_seconds = ticks / 20
    total_minutes = total_seconds / 60
    total_hours = total_minutes / 60

    return total_hours
