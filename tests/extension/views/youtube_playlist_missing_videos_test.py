import pytest

from extension.models import YoutubePlaylist


@pytest.fixture
def playlist(db):
    return YoutubePlaylist.objects.create(
        yp_name="SQLite Demo Playlist",
        yp_videos=[{"title": "Track A"}, {"title": "Track B"}],
    )


class TestYoutubePlaylistMissingVideos:
    URL = "/extension/youtube-playlist-missing-videos/playlist-token"

    def test_render_missing_videos_includes_section_headers(self, client):

        response = client.get(self.URL)

        assert response.status_code == 200

        html_content = response.content.decode("utf-8")

        assert "Missing Videos" in html_content
        assert "Videos not saved" in html_content
        assert "Extra track" in html_content
