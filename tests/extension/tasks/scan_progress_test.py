import pytest
from unittest.mock import Mock, patch
from extension.models import YoutubePlaylist
import json
import pytest

from extension.models import YoutubePlaylist
from extension.views.scan_youtube_playlist import PollYoutubePlaylist
from extension.views.youtube_playlist_missing_videos import YoutubePlaylistMissingVideos
from tests.extension.views.youtube_playlist_missing_videos_test import playlist


@pytest.fixture
def mock_missing_videos_dependencies():
    """Context manager style fixture to patch external YouTube calls cleanly."""
    with patch(
        "extension.views.youtube_playlist_missing_videos.get_youtube_info"
    ) as mock_info, patch(
        "extension.views.youtube_playlist_missing_videos.get_videos"
    ) as mock_videos, patch(
        "extension.views.youtube_playlist_missing_videos.YoutubePlaylist.objects.get"
    ) as mock_get:

        mock_info.return_value = {"title": "Demo Playlist"}
        mock_videos.return_value = [{"title": "Keep me"}, {"title": "Extra track"}]
        mock_get.return_value = Mock(
            yp_videos=[{"title": "Keep me"}, {"title": "Missing track"}]
        )

        yield


@pytest.fixture
def mock_celery_started():
    with patch("extension.views.scan_youtube_playlist.AsyncResult") as mock_async:
        mock_async.return_value.state = "STARTED"
        mock_async.return_value.info = {
            "current": 1,
            "total": 1,
            "percent": 100,
            "last_title": "Started title",
        }
        yield mock_async


def test_poll_includes_last_title_in_progress_state(db, client, mock_celery_progress):
    response = client.get(
        "/extension/poll-scan-youtube-playlist",
        data={"task_id": "task-123"},
        HTTP_X_API_KEY="test-token",
    )

    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "PROGRESS"
    assert data["current"] == 5
    assert data["total"] == 10
    assert data["percent"] == 50
    assert data["last_title"] == "Example title"


def test_poll_accepts_started_state_as_progress(db, client, mock_celery_started):
    response = client.get(
        "/extension/poll-scan-youtube-playlist",
        data={"task_id": "task-123"},
        HTTP_X_API_KEY="test-token",
    )

    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "STARTED"
    assert data["percent"] == 100
    assert data["last_title"] == "Started title"
