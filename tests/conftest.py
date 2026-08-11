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
    to ensure databases are whitelisted for every single execution.
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

        def normalize_url(target_url):
            normalized = target_url

            if normalized.startswith("https://"):
                normalized = normalized[len("https://") :]
            elif normalized.startswith("http://"):
                normalized = normalized[len("http://") :]

            while "//" in normalized:
                normalized = normalized.replace("//", "/")

            return normalized.strip("/")

        def side_effect(method, url, *args, **kwargs):
            history.append({"method": method, "url": url, "kwargs": kwargs})
            normalized_url = normalize_url(url)

            for pattern, data in responses.items():
                if normalize_url(pattern) in normalized_url:
                    response = mocker.Mock(status_code=data.get("status", 200))
                    response.json = mocker.Mock(return_value=data.get("json", {}))
                    response.text = data.get("text", "")
                    response.content = data.get("content", b"")
                    response.raise_for_status = mocker.Mock(return_value=None)

                    return response

            response = mocker.Mock(status_code=404)
            response.json = mocker.Mock(return_value={})
            response.text = ""
            response.content = b""
            response.raise_for_status = mocker.Mock(return_value=None)

            return response

        # Create the mock module
        mock_lib = mocker.Mock()

        # Mock get/post/put/delete/patch/head and generic request
        for method in ["get", "post", "put", "delete", "patch", "head"]:
            getattr(mock_lib, method).side_effect = (
                lambda url, m=method, *a, **k: side_effect(m, url, *a, **k)
            )

        def request_side_effect(method, url, *a, **k):
            return side_effect(method, url, *a, **k)

        mock_lib.request.side_effect = request_side_effect

        # Mock requests.Session() and its methods
        mock_session_instance = mocker.Mock()

        for method in ["get", "post", "put", "delete", "patch"]:
            getattr(mock_session_instance, method).side_effect = (
                lambda url, m=method, *a, **k: side_effect(m, url, *a, **k)
            )

        mock_session_instance.request.side_effect = request_side_effect
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


@pytest.fixture
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "django-db",
        "task_always_eager": False,
        "task_eager_propagates": True,
    }


def db(transactional_db):
    pass
