import json
from unittest.mock import patch

import pytest

from common.models import AppToken
from extension.models import YoutubePlaylist


class TestYoutubeSavePlaylistView:
    URL = "/extension/youtube-save-playlist"

    def test_returns_bad_request_for_invalid_json(self, client):
        response = client.post(
            self.URL,
            data="not-json",
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "JSON parse error - Expecting value: line 1 column 1 (char 0)"
        }

    def test_returns_bad_request_for_missing_url(self, client):
        response = client.post(
            self.URL,
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.json() == {"url": ["This field is required."]}

    @patch("extension.views.youtube_save_playlist.get_youtube_info")
    @patch("extension.views.youtube_save_playlist.get_videos")
    def test_creates_playlist(self, mock_get_videos, mock_get_youtube_info, client):
        mock_get_youtube_info.return_value = {
            "title": "My Playlist",
            "entries": [{"id": "abc123", "title": "Track 1"}],
        }
        mock_get_videos.return_value = [{"id": "abc123", "title": "Track 1"}]

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        assert response.content.decode() == "Save & Reload"
        assert mock_get_youtube_info.called
        assert mock_get_videos.called

    @patch("extension.views.youtube_save_playlist.get_youtube_info")
    @patch("extension.views.youtube_save_playlist.get_videos")
    def test_returns_bad_request_if_youtube_title_missing(
        self, mock_get_videos, mock_get_youtube_info, client
    ):
        mock_get_youtube_info.return_value = {"entries": []}
        mock_get_videos.return_value = []

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.content.decode() == "Youtube title not present"

    @patch("extension.views.youtube_save_playlist.get_youtube_info")
    @patch("extension.views.youtube_save_playlist.get_videos")
    def test_returns_bad_request_if_no_videos(
        self, mock_get_videos, mock_get_youtube_info, client
    ):
        mock_get_youtube_info.return_value = {"title": "My Playlist"}
        mock_get_videos.return_value = []

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 400
        assert response.content.decode() == "No videos found"

    @patch("extension.views.youtube_save_playlist.get_youtube_info")
    @patch("extension.views.youtube_save_playlist.get_videos")
    def test_update_playlist_removes_missing_videos(
        self, mock_get_videos, mock_get_youtube_info, client
    ):
        mock_get_youtube_info.return_value = {"title": "My Playlist"}
        mock_get_videos.return_value = [{"name": "new song"}]

        yp = YoutubePlaylist.objects.create(
            yp_name="My Playlist", yp_videos=[{"name": "song 1"}]
        )

        assert yp.yp_videos == [{"name": "song 1"}]

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        yp.refresh_from_db()

        assert yp.yp_videos == [{"name": "new song"}]

    @patch("extension.views.youtube_save_playlist.get_youtube_info")
    @patch("extension.views.youtube_save_playlist.get_videos")
    def test_update_playlist_adds_new_videos(
        self, mock_get_videos, mock_get_youtube_info, client
    ):
        mock_get_youtube_info.return_value = {"title": "My Playlist"}
        mock_get_videos.return_value = [
            {"name": "song 1"},
            {"name": "new song"},
        ]

        yp = YoutubePlaylist.objects.create(
            yp_name="My Playlist", yp_videos=[{"name": "song 1"}]
        )

        assert yp.yp_videos == [{"name": "song 1"}]

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="test-token",
        )

        assert response.status_code == 200
        yp.refresh_from_db()

        assert yp.yp_videos == [{"name": "song 1"}, {"name": "new song"}]

    def test_require_token_returns_403_when_missing_api_key(self, client):
        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert response.content.decode() == "Missing API token"

    def test_returns_403_for_invalid_api_key(self, client):
        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY="bad-token",
        )

        assert response.status_code == 403
        assert response.content.decode() == "Invalid or inactive token"

    def test_returns_403_for_inactive_api_key(self, client):
        token = AppToken.objects.get(at_app_name="extension")
        token.at_is_active = False
        token.save()

        response = client.post(
            self.URL,
            data=json.dumps({"url": "PL123"}),
            content_type="application/json",
            HTTP_X_API_KEY=token.at_app_token,
        )

        assert response.status_code == 403
        assert response.content.decode() == "Invalid or inactive token"
