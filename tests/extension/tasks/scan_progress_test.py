import json
import unittest
from unittest.mock import Mock, patch

from django.test import Client, RequestFactory, TestCase, override_settings

from extension.models import YoutubePlaylist
from extension.views.scan_youtube_playlist import PollYoutubePlaylist
from extension.views.youtube_playlist_missing_videos import YoutubePlaylistMissingVideos


class YoutubePlaylistMissingVideosTests(unittest.TestCase):
    @patch(
        "extension.views.youtube_playlist_missing_videos.YoutubePlaylist.objects.get"
    )
    @patch("extension.views.youtube_playlist_missing_videos.get_videos")
    @patch("extension.views.youtube_playlist_missing_videos.get_youtube_info")
    def test_render_missing_videos_includes_section_headers(
        self, mock_get_youtube_info, mock_get_videos, mock_playlist_get
    ):
        mock_get_youtube_info.return_value = {"title": "Demo Playlist"}
        mock_get_videos.return_value = [
            {"title": "Keep me"},
            {"title": "Extra track"},
        ]
        mock_playlist_get.return_value = Mock(
            yp_videos=[{"title": "Keep me"}, {"title": "Missing track"}]
        )

        view = YoutubePlaylistMissingVideos()

        html = view.render_missing_videos("playlist-token")

        self.assertIn("Missing Videos", html)
        self.assertIn("Videos not saved", html)
        self.assertIn("Extra track", html)


class YoutubePlaylistModelTests(TestCase):
    databases = "__all__"

    def test_playlist_record_is_persisted_in_sqlite_test_db(self):
        playlist = YoutubePlaylist.objects.create(
            yp_name="SQLite Demo Playlist",
            yp_videos=[{"title": "Track A"}, {"title": "Track B"}],
        )

        saved_playlist = YoutubePlaylist.objects.get(yp_name="SQLite Demo Playlist")

        self.assertEqual(saved_playlist.pk, playlist.pk)
        self.assertEqual(saved_playlist.yp_videos[0]["title"], "Track A")
        self.assertEqual(len(saved_playlist.yp_videos), 2)


class PollYoutubePlaylistTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(
        CORS_ALLOWED_ORIGINS=["chrome-extension://hembbpkpgfcokkcilfnjoconplajoogh"],
        ALLOWED_HOSTS=["testserver"],
    )
    def test_extension_preflight_request_includes_cors_headers(self):
        client = Client()

        response = client.options(
            "/extension/youtube-playlist-missing-videos/test-token/PL8YLENsJaBBIePURficqYL9TvE6mOcK2g",
            HTTP_ORIGIN="chrome-extension://hembbpkpgfcokkcilfnjoconplajoogh",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "chrome-extension://hembbpkpgfcokkcilfnjoconplajoogh",
        )
        self.assertIn("GET", response["Access-Control-Allow-Methods"])

    @patch("extension.views.scan_youtube_playlist.AsyncResult")
    def test_poll_includes_last_title_in_progress_state(self, mock_async_result):
        mock_async_result.return_value.state = "PROGRESS"
        mock_async_result.return_value.info = {
            "current": 5,
            "total": 10,
            "percent": 50,
            "last_title": "Example title",
        }

        request = self.factory.get(
            "/extension/poll-scan-youtube-playlist?task_id=task-123",
            HTTP_X_API_KEY="test-token",
        )

        view = PollYoutubePlaylist()
        response = PollYoutubePlaylist.get.__wrapped__(view, request)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data["state"], "PROGRESS")
        self.assertEqual(data["current"], 5)
        self.assertEqual(data["total"], 10)
        self.assertEqual(data["percent"], 50)
        self.assertEqual(data["last_title"], "Example title")

    @patch("extension.views.scan_youtube_playlist.AsyncResult")
    def test_poll_accepts_started_state_as_progress(self, mock_async_result):
        mock_async_result.return_value.state = "STARTED"
        mock_async_result.return_value.info = {
            "current": 1,
            "total": 1,
            "percent": 100,
            "last_title": "Started title",
        }

        request = self.factory.get(
            "/extension/poll-scan-youtube-playlist?task_id=task-123",
            HTTP_X_API_KEY="test-token",
        )

        view = PollYoutubePlaylist()
        response = PollYoutubePlaylist.get.__wrapped__(view, request)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEqual(data["state"], "STARTED")
        self.assertEqual(data["percent"], 100)
        self.assertEqual(data["last_title"], "Started title")
