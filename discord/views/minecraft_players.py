import json

from rest_framework.views import APIView
from dataclasses import dataclass

from django.http import HttpResponseBadRequest, HttpResponse
from django.utils.decorators import method_decorator
from common.auth.decorators import require_token, validate_arguments

from common.auth.backends import app_auth
from discord.models import MinecraftPlayer


@dataclass
class Args:
    mc_server_id: str
    mc_players: list


class MinecraftPlayersView(APIView):

    @method_decorator([require_token(app_name="discord"), validate_arguments(Args)])
    def post(self, request, args: Args):

        mc_server_id = args.mc_server_id
        mc_players = args.mc_players

        if not mc_server_id:
            return HttpResponseBadRequest("Missing identifier")

        existing_uuids = set(
            str(u)
            for u in MinecraftPlayer.objects.filter(
                mp_mcs_server_id=mc_server_id
            ).values_list("mp_uuid", flat=True)
        )

        to_create = []
        for player in mc_players:
            uuid = player.get("uuid")
            name = player.get("name")

            if not uuid or not name:
                continue

            if uuid not in existing_uuids:
                to_create.append(
                    MinecraftPlayer(
                        mp_uuid=uuid,
                        mp_mc_name=name,
                        mp_mcs_server_id=mc_server_id,
                    )
                )

        if to_create:
            MinecraftPlayer.objects.bulk_create(to_create, batch_size=100)
            return HttpResponse(status=201)

        return HttpResponse(status=200)
