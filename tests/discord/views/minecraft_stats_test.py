import json
import uuid

from discord.models import MinecraftPlayer, MinecraftServer, MinecraftStat


class TestMinecraftStatsView:
    URL = "/discord/minecraft-stats"

    def test_creates_stat_for_existing_player(self, client):
        server = MinecraftServer.objects.create(mcs_name="Test Server")
        player_uuid = uuid.uuid4()
        player = MinecraftPlayer.objects.create(
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
                    "uuid": str(player_uuid),
                    "mc_server_id": str(server.mcs_id),
                    "stats": {
                        "stats": {
                            "minecraft:custom": {
                                "minecraft:play_time": 1200,
                                "minecraft:deaths": 2,
                                "minecraft:player_kills": 3,
                                "minecraft:mob_kills": 4,
                            }
                        }
                    },
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 201
        assert MinecraftStat.objects.filter(mst_player=player).exists()

    def test_get_returns_aggregated_player_stats(self, client):
        server = MinecraftServer.objects.create(mcs_name="Test Server")
        player_uuid = uuid.uuid4()
        player = MinecraftPlayer.objects.create(
            mp_uuid=player_uuid,
            mp_mc_name="Steve",
            mp_ds_user_id="user1",
            mp_ds_quild_id="guild1",
            mp_mcs_server=server,
        )

        MinecraftStat.objects.create(
            mst_data={
                "stats": {
                    "minecraft:custom": {
                        "minecraft:play_time": 1200,
                        "minecraft:deaths": 2,
                        "minecraft:player_kills": 3,
                        "minecraft:mob_kills": 4,
                    }
                }
            },
            mst_player=player,
        )

        response = client.get(
            self.URL,
            {"quild_id": "guild1"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload[0]["mc_name"] == "Steve"
        assert payload[0]["deaths"] == 2
        assert payload[0]["player_kills"] == 3
        assert payload[0]["mob_kills"] == 4

    def test_returns_bad_request_for_unknown_player(self, client):
        server = MinecraftServer.objects.create(mcs_name="Test Server")

        response = client.post(
            self.URL,
            data=json.dumps(
                {
                    "uuid": str(uuid.uuid4()),
                    "mc_server_id": str(server.mcs_id),
                    "stats": {"stats": {}},
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.content.decode() == "Unknown Player"
