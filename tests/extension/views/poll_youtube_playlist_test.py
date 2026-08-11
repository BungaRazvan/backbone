import pytest

from extension.tasks.scan_playlist import scan_youtube_playlist

from .scan_youtube_playlist_test import mock_yt_dlp, celery_includes


class TestPollScanYoutubePlaylistView:
    URL = "/extension/poll-scan-youtube-playlist"

    @pytest.mark.django_db(transaction=True)
    def test_reports_success(self, client, celery_app, celery_worker, mock_yt_dlp):
        with mock_yt_dlp():

            task = scan_youtube_playlist.delay("PL123")
            task_id = task.id

            poll_response = client.get(
                self.URL,
                data={"task_id": task_id},
                HTTP_X_API_KEY="test-token",
            )

            assert poll_response.status_code == 200
            data = poll_response.json()

            assert data["state"] == "PENDING"
            assert data["percent"] == 0
            assert data["last_title"] == "Scan is starting..."

            result = celery_app.AsyncResult(task_id)
            result.get(timeout=2.0)

            poll_response = client.get(
                self.URL,
                data={"task_id": task_id},
                HTTP_X_API_KEY="test-token",
            )
            data = poll_response.json()

            assert data["state"] == "SUCCESS"
            assert data["percent"] == 100
            assert data["last_title"] == "Scan complete"
            assert data["total"] == 1
            assert data["result"]["unavailable_count"] == 0
            assert data["result"]["unavailable_tracks"] == []
