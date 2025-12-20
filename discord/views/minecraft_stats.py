from rest_framework.views import APIView

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from common.utils import require_token
from discord.models import MinecraftStat, MinecraftPlayer

import json


class MinecraftStatsView(APIView):
    @require_token("discord")
    def post(self, request):

        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("Invalid request")

        uuid = data.get("uuid")
        stats = data.get("stats")
        mc_server_id = data.get("mc_server_id")

        if not uuid:
            return HttpResponseBadRequest("Missing identifier")

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

    @require_token("discord")
    def get(self, request):
        args = request.GET

        ds_quild_id = args.get("quild_id")

        if not ds_quild_id:
            return HttpResponseBadRequest("Missing arguments")

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
