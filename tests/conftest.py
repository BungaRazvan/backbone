import pytest
import socket
import pytest

from django.conf import settings
from django.test import TestCase, TransactionTestCase


@pytest.fixture(scope="session", autouse=True)
def configure_global_test_databases():
    """
    Runs once per session. Forces Django's base test runners
    to always look at and prepare all defined database aliases.
    """
    all_dbs = set(settings.DATABASES.keys())
    TestCase.databases = all_dbs
    TransactionTestCase.databases = all_dbs


@pytest.fixture(autouse=True)
def enable_multidb_access(db, request):
    """
    Runs per test. Dynamically patches pytest-django's runtime test wrapper
    to ensure 'extension_db' is whitelisted for every single execution.
    """
    django_case = getattr(request.node, "_parent_test_case", None)
    if django_case:
        django_case.databases = list(settings.DATABASES.keys())


@pytest.fixture
def mock_requests(mocker):
    """
    A global fixture to mock the 'requests' library in any module.
    Usage: mock_requests("app_name.module_name", responses={...})
    """

    def _setup_mock(target_path, responses=None):
        responses = responses or {}
        history = []

        def side_effect(method, url, *args, **kwargs):
            history.append({"method": method, "url": url, "kwargs": kwargs})
            for pattern, data in responses.items():
                if pattern in url:
                    return mocker.Mock(
                        status_code=data.get("status", 200),
                        json=lambda: data.get("json", {}),
                        text=data.get("text", ""),
                        content=data.get("content", b""),
                        raise_for_status=lambda: None,
                    )
            return mocker.Mock(status_code=404)

        # Create the mock module
        mock_lib = mocker.Mock()

        # Mock methods: requests.get, requests.post, etc.
        for method in ["get", "post", "put", "delete", "patch", "head"]:
            getattr(mock_lib, method).side_effect = (
                lambda url, m=method, *a, **k: side_effect(m, url, *a, **k)
            )

        # Mock requests.Session() and its methods
        mock_session_instance = mocker.Mock()
        for method in ["get", "post", "put", "delete", "patch"]:
            getattr(mock_session_instance, method).side_effect = (
                lambda url, m=method, *a, **k: side_effect(m, url, *a, **k)
            )
        mock_lib.Session.return_value = mock_session_instance

        # Patch the specific module that imports requests
        mocker.patch(f"{target_path}.requests", mock_lib)

        return history

    return _setup_mock


@pytest.fixture(autouse=True)
def block_external_requests(monkeypatch):
    original_getaddrinfo = socket.getaddrinfo
    ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}

    def assert_only_localhost(host, *args, **kwargs):
        assert host in ALLOWED_HOSTS, f"External request to {host} detected"
        return original_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", assert_only_localhost)
