import pytest

from common.models import AppToken


@pytest.fixture(autouse=True)
def mytools_api_token():
    AppToken.objects.create(
        at_app_name="mytools", at_app_token="test-token", at_is_active=True
    )
