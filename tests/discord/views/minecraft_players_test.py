import json
from urllib import response
import uuid

from discord.models import MinecraftPlayer, MinecraftServer


class TestMinecraftPlayersView:
    URL = "/discord/minecraft-players"

    def test_creates_new_players(self, client):
        server = MinecraftServer.objects.create(mcs_name="Test Server")
        player_uuid = uuid.uuid4()

        response = client.post(
            self.URL,
            data=json.dumps(
                {
                    "mc_server_id": str(server.mcs_id),
                    "mc_players": [{"uuid": str(player_uuid), "name": "Steve"}],
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 201
        assert MinecraftPlayer.objects.filter(mp_mcs_server=server).count() == 1

    def test_returns_200_when_players_already_exist(self, client):
        server = MinecraftServer.objects.create(mcs_name="Test Server")
        player_uuid = uuid.uuid4()
        MinecraftPlayer.objects.create(
            mp_uuid=player_uuid,
            mp_mc_name="Steve",
            mp_ds_user_id="user1",
            mp_ds_quild_id="guild1",
            mp_mcs_server=server,
        )

        response = client.post(
            self.URL,
            data=json.dumps(
                {
                    "mc_server_id": str(server.mcs_id),
                    "mc_players": [{"uuid": str(player_uuid), "name": "Steve"}],
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )
        assert response.status_code == 200
        assert MinecraftPlayer.objects.filter(mp_mcs_server=server).count() == 1

    def test_returns_bad_request_for_invalid_payload(self, client):
        response = client.post(
            self.URL,
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.json() == {
            "mc_server_id": ["This field is required."],
            "mc_players": ["This field is required."],
        }
