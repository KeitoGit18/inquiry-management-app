import sqlite3
from urllib.parse import urlsplit

import pytest


def assert_redirects_to(response, expected_path):
    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == expected_path


def test_database_is_created_in_temporary_directory(app_module, tmp_path):
    assert app_module.DATABASE_PATH == tmp_path / "instance" / "inquiries.db"
    assert app_module.DATABASE_PATH.is_file()


def test_public_post_creates_inquiry(client, app_module):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "content": "Please send more information.",
    }

    response = client.post("/api/inquiries", json=payload)

    assert response.status_code == 201
    created = response.get_json()
    assert isinstance(created["id"], int)
    assert created["name"] == payload["name"]
    assert created["email"] == payload["email"]
    assert created["content"] == payload["content"]
    assert created["status"] == app_module.STATUS_OPEN
    assert created["created_at"]

    connection = sqlite3.connect(app_module.DATABASE_PATH)

    try:
        saved = connection.execute(
            """
            SELECT id, name, email, content, status
            FROM inquiries
            WHERE id = ?
            """,
            (created["id"],),
        ).fetchone()
    finally:
        connection.close()

    assert saved == (
        created["id"],
        payload["name"],
        payload["email"],
        payload["content"],
        app_module.STATUS_OPEN,
    )


@pytest.mark.parametrize("blank_field", ["name", "email", "content"])
def test_public_post_rejects_blank_required_fields(client, blank_field):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "content": "Question",
    }
    payload[blank_field] = "   "

    response = client.post("/api/inquiries", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_public_post_rejects_missing_fields(client):
    response = client.post("/api/inquiries", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_public_post_rejects_invalid_email(client):
    response = client.post(
        "/api/inquiries",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "content": "Question",
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_public_post_rejects_malformed_json(client):
    response = client.post(
        "/api/inquiries",
        data="{not-json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_admin_page_redirects_unauthenticated_user(client):
    response = client.get("/admin")

    assert_redirects_to(response, "/admin/login")


@pytest.mark.parametrize("invalid_field", ["username", "password"])
def test_wrong_credentials_do_not_log_in(
    client,
    admin_credentials,
    invalid_field,
):
    submitted = admin_credentials.copy()
    submitted[invalid_field] = "incorrect"

    response = client.post("/admin/login", data=submitted)

    assert response.status_code == 200
    with client.session_transaction() as session_data:
        assert session_data.get("is_admin") is not True
    assert_redirects_to(client.get("/admin"), "/admin/login")


def test_correct_credentials_log_in(client, admin_credentials):
    response = client.post("/admin/login", data=admin_credentials)

    assert_redirects_to(response, "/admin")
    with client.session_transaction() as session_data:
        assert session_data.get("is_admin") is True
    assert client.get("/admin").status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "request_options"),
    [
        ("get", "/api/inquiries", {}),
        (
            "patch",
            "/api/inquiries/1/status",
            {"json": {"status": "対応済み"}},
        ),
        ("delete", "/api/inquiries/1", {}),
    ],
)
def test_inquiry_apis_reject_unauthenticated_requests(
    client,
    method,
    path,
    request_options,
):
    response = getattr(client, method)(path, **request_options)

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_authenticated_user_can_list_update_and_delete_inquiries(
    client,
    app_module,
    admin_credentials,
):
    create_response = client.post(
        "/api/inquiries",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "content": "Question",
        },
    )
    assert create_response.status_code == 201
    inquiry_id = create_response.get_json()["id"]

    login_response = client.post("/admin/login", data=admin_credentials)
    assert_redirects_to(login_response, "/admin")

    list_response = client.get("/api/inquiries")
    assert list_response.status_code == 200
    inquiries = list_response.get_json()
    assert [inquiry["id"] for inquiry in inquiries] == [inquiry_id]

    update_response = client.patch(
        f"/api/inquiries/{inquiry_id}/status",
        json={"status": app_module.STATUS_DONE},
    )
    assert update_response.status_code == 200
    assert update_response.get_json() == {
        "id": inquiry_id,
        "status": app_module.STATUS_DONE,
    }

    updated_list = client.get("/api/inquiries").get_json()
    assert updated_list[0]["status"] == app_module.STATUS_DONE

    delete_response = client.delete(f"/api/inquiries/{inquiry_id}")
    assert delete_response.status_code == 200
    assert delete_response.get_json()["id"] == inquiry_id

    final_list_response = client.get("/api/inquiries")
    assert final_list_response.status_code == 200
    assert final_list_response.get_json() == []
