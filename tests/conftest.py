import pytest
import socket
import requests

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
    """Global fixture to mock 'requests' with backward compatibility and per-method support."""

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

        def create_mock_response(
            status=200, json_data=None, text="", content=b"", url=""
        ):
            response = mocker.Mock(
                status_code=status,
                reason="OK" if status < 400 else "HTTP Error",
                url=url or "https://api.example.com",
            )
            response.json = mocker.Mock(return_value=json_data or {})
            response.text = text
            response.content = content

            # Attach real raise_for_status so HTTP 4xx/5xx actually throw HTTPError
            response.raise_for_status = (
                requests.models.Response.raise_for_status.__get__(
                    response, requests.models.Response
                )
            )

            return response

        def side_effect(method, url, *args, **kwargs):
            history.append({"method": method, "url": url, "kwargs": kwargs})
            normalized_url = normalize_url(url)
            method_upper = method.upper()

            for pattern, raw_config in responses.items():
                if normalize_url(pattern) in normalized_url:
                    # Backward compatibility check:
                    # If raw_config contains HTTP method keys, resolve the specific method's config.
                    # Otherwise, treat raw_config as the global response dict for all methods.
                    if any(
                        m in raw_config
                        for m in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
                    ):
                        data = raw_config.get(method_upper)
                        if data is None:
                            continue  # Method not matched for this pattern
                    else:
                        data = raw_config

                    # Support raising direct network/connection exceptions
                    if "exception" in data:
                        raise data["exception"]

                    return create_mock_response(
                        status=data.get("status", 200),
                        json_data=data.get("json", {}),
                        text=data.get("text", ""),
                        content=data.get("content", b""),
                        url=url,
                    )

            return create_mock_response(status=404, url=url)

        mock_lib = mocker.Mock()
        methods = ["get", "post", "put", "delete", "patch", "head"]

        def make_handler(m):
            return lambda url, *args, **kwargs: side_effect(m, url, *args, **kwargs)

        for m in methods:
            getattr(mock_lib, m).side_effect = make_handler(m)

        mock_lib.request.side_effect = lambda method, url, *args, **kwargs: side_effect(
            method, url, *args, **kwargs
        )

        mock_session_instance = mocker.Mock()
        for m in methods:
            getattr(mock_session_instance, m).side_effect = make_handler(m)

        mock_session_instance.request.side_effect = (
            lambda method, url, *args, **kwargs: side_effect(
                method, url, *args, **kwargs
            )
        )
        mock_lib.Session.return_value = mock_session_instance

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


@pytest.fixture(autouse=True)
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "django-db",
        "task_always_eager": False,
        "task_eager_propagates": True,
    }


def db(transactional_db):
    pass
