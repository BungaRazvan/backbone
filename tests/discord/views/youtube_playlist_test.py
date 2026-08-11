import json

from discord.models import YoutubePlaylist, YoutubeSong


class TestYoutubePlaylistView:
    URL = "/discord/youtube-playlist"

    def test_create_playlist(self, client):
        response = client.post(
            self.URL,
            data=json.dumps(
                {
                    "user_id": "user1",
                    "guild_id": "guild1",
                    "playlist_name": "My Playlist",
                    "playlist_songs": "https://youtu.be/abc123 https://youtu.be/def456",
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.content.decode() == "Playlist created"
        playlist = YoutubePlaylist.objects.get(yp_user_id="user1", yp_guild_id="guild1")
        assert playlist.songs.count() == 2

    def test_modify_playlist(self, client):
        playlist = YoutubePlaylist.objects.create(
            yp_name="My Playlist",
            yp_user_id="user1",
            yp_guild_id="guild1",
        )

        response = client.put(
            self.URL,
            data=json.dumps(
                {
                    "user_id": "user1",
                    "guild_id": "guild1",
                    "playlist_id": str(playlist.yp_id),
                    "playlist_name": "Updated Playlist",
                    "playlist_songs": "https://youtu.be/xyz789",
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.content.decode() == "Playlist Modified"
        playlist.refresh_from_db()
        assert playlist.yp_name == "Updated Playlist"
        assert playlist.songs.count() == 1

    def test_delete_playlist(self, client):
        playlist = YoutubePlaylist.objects.create(
            yp_name="My Playlist",
            yp_user_id="user1",
            yp_guild_id="guild1",
        )

        response = client.delete(
            self.URL,
            data=json.dumps(
                {
                    "user_id": "user1",
                    "guild_id": "guild1",
                    "playlist_id": str(playlist.yp_id),
                }
            ),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.content.decode() == "Playlist Deleted"
        assert not YoutubePlaylist.objects.filter(yp_id=playlist.yp_id).exists()

    def test_get_returns_playlist_data(self, client):
        playlist = YoutubePlaylist.objects.create(
            yp_name="My Playlist",
            yp_user_id="user1",
            yp_guild_id="guild1",
        )
        YoutubeSong.objects.create(
            ys_url="https://youtu.be/abc123", ys_playlist=playlist
        )

        response = client.get(
            self.URL,
            {"user_id": "user1", "guild_id": "guild1"},
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["playlists"][0]["id"] == playlist.yp_id
        assert payload["playlists"][0]["songs"] == ["https://youtu.be/abc123"]
