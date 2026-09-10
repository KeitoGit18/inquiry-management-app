import re

import pytest


def valid_inquiry():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "content": "Question",
    }


def assert_security_headers(response, app_module):
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == (
        app_module.CONTENT_SECURITY_POLICY
    )


@pytest.mark.parametrize(
    ("tag_name", "field_name"),
    [
        ("input", "name"),
        ("input", "email"),
        ("textarea", "content"),
    ],
)
def test_public_form_has_maxlength_attributes(
    client,
    app_module,
    tag_name,
    field_name,
):
    response = client.get("/")
    html = response.get_data(as_text=True)
    maximum_length = app_module.INQUIRY_FIELD_LIMITS[field_name]

    assert re.search(
        rf'<{tag_name}[^>]*id="{field_name}"[^>]*maxlength="{maximum_length}"',
        html,
    )


def test_public_api_accepts_values_at_maximum_length(client, app_module):
    email_suffix = "@example.com"
    payload = {
        "name": "n" * app_module.INQUIRY_FIELD_LIMITS["name"],
        "email": "e"
        * (app_module.INQUIRY_FIELD_LIMITS["email"] - len(email_suffix))
        + email_suffix,
        "content": "c" * app_module.INQUIRY_FIELD_LIMITS["content"],
    }

    response = client.post("/api/inquiries", json=payload)

    assert response.status_code == 201


@pytest.mark.parametrize("field_name", ["name", "email", "content"])
def test_public_api_rejects_values_over_maximum_length(
    client,
    app_module,
    field_name,
):
    payload = valid_inquiry()
    maximum_length = app_module.INQUIRY_FIELD_LIMITS[field_name]

    if field_name == "email":
        email_suffix = "@example.com"
        payload[field_name] = (
            "e" * (maximum_length + 1 - len(email_suffix)) + email_suffix
        )
    else:
        payload[field_name] = "x" * (maximum_length + 1)

    response = client.post("/api/inquiries", json=payload)

    assert response.status_code == 400
    assert str(maximum_length) in response.get_json()["error"]


def test_public_api_rejects_oversized_request(client, app_module):
    oversized_body = b"x" * (app_module.app.config["MAX_CONTENT_LENGTH"] + 1)

    response = client.post(
        "/api/inquiries",
        data=oversized_body,
        content_type="application/json",
    )

    assert response.status_code == 413
    assert response.get_json() == {
        "error": app_module.REQUEST_TOO_LARGE_ERROR_MESSAGE,
    }
    assert_security_headers(response, app_module)


def test_responses_include_security_headers(client, app_module):
    response = client.get("/")

    assert response.status_code == 200
    assert_security_headers(response, app_module)

    policy = response.headers["Content-Security-Policy"]
    for directive in (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ):
        assert directive in policy
    assert "'unsafe-inline'" not in policy


def test_local_login_cookie_is_safe_without_requiring_https(
    client,
    app_module,
    admin_credentials,
):
    response = client.post("/admin/login", data=admin_credentials)
    cookie = response.headers["Set-Cookie"]

    assert app_module.app.config["DEBUG"] is False
    assert app_module.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app_module.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app_module.app.config["SESSION_COOKIE_SECURE"] is False
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "; Secure" not in cookie


@pytest.mark.parametrize(
    "app_module",
    [{"APP_ENV": "production", "FLASK_DEBUG": "1"}],
    indirect=True,
)
def test_production_login_cookie_requires_https_and_debug_stays_disabled(
    client,
    app_module,
    admin_credentials,
):
    response = client.post(
        "/admin/login",
        data=admin_credentials,
        base_url="https://localhost",
    )
    cookie = response.headers["Set-Cookie"]

    assert app_module.app.config["DEBUG"] is False
    assert app_module.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app_module.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app_module.app.config["SESSION_COOKIE_SECURE"] is True
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "; Secure" in cookie


def test_public_form_rate_limit_returns_japanese_error(client, app_module):
    for request_number in range(10):
        payload = valid_inquiry()
        payload["email"] = f"test{request_number}@example.com"
        assert client.post("/api/inquiries", json=payload).status_code == 201

    response = client.post("/api/inquiries", json=valid_inquiry())

    assert response.status_code == 429
    assert response.get_json() == {
        "error": app_module.RATE_LIMIT_ERROR_MESSAGE,
    }
    assert_security_headers(response, app_module)


def test_login_rate_limit_counts_only_post_and_shows_japanese_error(
    client,
    app_module,
    admin_credentials,
):
    invalid_credentials = {
        **admin_credentials,
        "password": "incorrect",
    }

    for _ in range(10):
        assert client.get("/admin/login").status_code == 200

    for _ in range(5):
        response = client.post("/admin/login", data=invalid_credentials)
        assert response.status_code == 200

    response = client.post("/admin/login", data=invalid_credentials)
    html = response.get_data(as_text=True)

    assert response.status_code == 429
    assert app_module.RATE_LIMIT_ERROR_MESSAGE in html
    assert 'role="alert"' in html
    assert_security_headers(response, app_module)
