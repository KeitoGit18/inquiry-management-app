import importlib
import sys
from pathlib import Path

import dotenv
import flask
import pytest
from werkzeug.security import generate_password_hash


TEST_ADMIN_USERNAME = "pytest-admin"
TEST_ADMIN_PASSWORD = "pytest-password"


@pytest.fixture
def app_module(tmp_path, monkeypatch, request):
    """Load the application without touching the real .env or instance DB."""
    instance_path = tmp_path / "instance"
    project_root = Path(__file__).resolve().parents[1]

    monkeypatch.syspath_prepend(str(project_root))
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        flask.Flask,
        "auto_find_instance_path",
        lambda self: str(instance_path),
    )
    test_environment = {
        "SECRET_KEY": "pytest-only-secret-key",
        "ADMIN_USERNAME": TEST_ADMIN_USERNAME,
        "ADMIN_PASSWORD_HASH": generate_password_hash(TEST_ADMIN_PASSWORD),
        "APP_ENV": "development",
        "RATELIMIT_STORAGE_URI": "memory://",
        "FLASK_DEBUG": "0",
    }
    test_environment.update(getattr(request, "param", {}))

    for name, value in test_environment.items():
        monkeypatch.setenv(name, value)

    sys.modules.pop("app", None)
    module = None

    try:
        module = importlib.import_module("app")
        module.app.config.update(TESTING=True)

        assert Path(module.app.instance_path) == instance_path
        assert module.DATABASE_PATH == instance_path / "inquiries.db"

        yield module
    finally:
        if module is not None:
            module.limiter.reset()
        sys.modules.pop("app", None)


@pytest.fixture
def client(app_module):
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def admin_credentials():
    return {
        "username": TEST_ADMIN_USERNAME,
        "password": TEST_ADMIN_PASSWORD,
    }
