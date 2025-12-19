from rest_framework.views import APIView

from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse

from common.utils import require_token
from discord.models import MinecraftPlayer

import json


class MinecraftPlayersView(APIView):
    @require_token("discord")
    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            return HttpResponseBadRequest("Invalid request")

        mc_server_id = data.get("mc_server_id")
        mc_players = data.get("mc_players") or []

        if not mc_server_id:
            return HttpResponseBadRequest("Missing identifier")

        uuids = list(
            MinecraftPlayer.objects.all(mp_mcs_server_id=mc_server_id).values_list(
                "mp_uuid", flat=True
            )
        )

        to_create = []
        for player in mc_players:
            uuid = player.get("uuid")
            name = player.get("name")

            if not uuid or not name:
                continue

            if uuid not in uuids:
                to_create.append(
                    MinecraftPlayer(
                        mp_uuid=uuid,
                        mp_name=name,
                        mp_mcs_server_id=mc_server_id,
                    )
                )

        if to_create:
            MinecraftPlayer.objects.bulk_create(to_create, batch_size=100)
            return HttpResponse(status=201)

        return HttpResponse(status=200)
