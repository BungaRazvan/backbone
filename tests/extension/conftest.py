import pytest
from common.models import AppToken


@pytest.fixture(autouse=True)
def token(db):
    AppToken.objects.create(at_app_name="extension", at_app_token="test-token")
