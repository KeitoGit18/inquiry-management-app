import hmac
import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash


load_dotenv(Path(__file__).with_name(".env"))


INQUIRY_FIELD_LIMITS = {
    "name": 100,
    "email": 254,
    "content": 5000,
}
INQUIRY_FIELD_LABELS = {
    "name": "名前",
    "email": "メールアドレス",
    "content": "問い合わせ内容",
}
MAX_REQUEST_SIZE_BYTES = 64 * 1024
LOGIN_RATE_LIMIT = "5 per minute"
INQUIRY_RATE_LIMIT = "10 per minute"
RATE_LIMIT_ERROR_MESSAGE = (
    "短時間に操作が集中しました。しばらく待ってから、もう一度お試しください。"
)
REQUEST_TOO_LARGE_ERROR_MESSAGE = (
    "リクエストのサイズが大きすぎます。入力内容を短くして、もう一度お試しください。"
)
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "connect-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


def get_required_environment_variable(name):
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"{name}が設定されていません。.envに必要な設定を追加してください。"
        )

    return value


APP_ENV = os.environ.get("APP_ENV", "development").strip().lower() or "development"
IS_PRODUCTION = APP_ENV == "production"
RATE_LIMIT_STORAGE_URI = (
    os.environ.get("RATELIMIT_STORAGE_URI", "memory://").strip() or "memory://"
)


app = Flask(__name__, instance_relative_config=True)
app.config.update(
    DEBUG=False,
    MAX_CONTENT_LENGTH=MAX_REQUEST_SIZE_BYTES,
    RATELIMIT_HEADERS_ENABLED=True,
    RATELIMIT_STORAGE_URI=RATE_LIMIT_STORAGE_URI,
    SECRET_KEY=get_required_environment_variable("SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=app.config["RATELIMIT_STORAGE_URI"],
)
DATABASE_PATH = Path(app.instance_path) / "inquiries.db"
STATUS_OPEN = "未対応"
STATUS_DONE = "対応済み"
VALID_STATUSES = {STATUS_OPEN, STATUS_DONE}
ADMIN_USERNAME = get_required_environment_variable("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = get_required_environment_variable("ADMIN_PASSWORD_HASH")


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    connection = get_db_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


init_db()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


@app.errorhandler(413)
def request_too_large(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": REQUEST_TOO_LARGE_ERROR_MESSAGE}), 413

    return render_template("login.html", error=REQUEST_TOO_LARGE_ERROR_MESSAGE), 413


@app.errorhandler(429)
def rate_limit_exceeded(error):
    if request.path == "/admin/login":
        return render_template("login.html", error=RATE_LIMIT_ERROR_MESSAGE), 429

    return jsonify({"error": RATE_LIMIT_ERROR_MESSAGE}), 429


def is_admin_logged_in():
    return session.get("is_admin") is True


def admin_page_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_admin_logged_in():
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped_view


def admin_api_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({"error": "ログインが必要です。"}), 401

        return view(*args, **kwargs)

    return wrapped_view


def credentials_are_valid(username, password):
    try:
        password_is_valid = check_password_hash(ADMIN_PASSWORD_HASH, password)
    except ValueError:
        password_is_valid = False

    username_is_valid = hmac.compare_digest(username, ADMIN_USERNAME)
    return username_is_valid and password_is_valid


@app.route("/")
def index():
    return render_template(
        "index.html",
        inquiry_field_limits=INQUIRY_FIELD_LIMITS,
    )


@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit(LOGIN_RATE_LIMIT, methods=["POST"])
def admin_login():
    if is_admin_logged_in():
        return redirect(url_for("admin"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if credentials_are_valid(username, password):
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin"))

        error = "ユーザー名またはパスワードが正しくありません。"

    return render_template("login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
@admin_page_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_page_required
def admin():
    return render_template("admin.html")


@app.route("/api/inquiries", methods=["GET"])
@admin_api_required
def get_inquiries():
    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, name, email, content, status, created_at
            FROM inquiries
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        connection.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/inquiries", methods=["POST"])
@limiter.limit(INQUIRY_RATE_LIMIT)
def create_inquiry():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON形式のリクエスト本文を指定してください。"}), 400

    name = data.get("name")
    email = data.get("email")
    content = data.get("content")

    if not all(isinstance(value, str) for value in (name, email, content)):
        return jsonify({"error": "名前、メールアドレス、問い合わせ内容は文字列で入力してください。"}), 400

    name = name.strip()
    email = email.strip()
    content = content.strip()

    if not name or not email or not content:
        return jsonify({"error": "名前、メールアドレス、問い合わせ内容は必須です。"}), 400

    field_values = {
        "name": name,
        "email": email,
        "content": content,
    }

    for field_name, value in field_values.items():
        maximum_length = INQUIRY_FIELD_LIMITS[field_name]

        if len(value) > maximum_length:
            field_label = INQUIRY_FIELD_LABELS[field_name]
            return jsonify(
                {"error": f"{field_label}は{maximum_length}文字以内で入力してください。"}
            ), 400

    if "@" not in email:
        return jsonify({"error": "メールアドレスの形式が正しくありません。"}), 400

    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO inquiries (name, email, content, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email, content, STATUS_OPEN, created_at),
        )
        connection.commit()
    finally:
        connection.close()

    return jsonify(
        {
            "id": cursor.lastrowid,
            "name": name,
            "email": email,
            "content": content,
            "status": STATUS_OPEN,
            "created_at": created_at,
        }
    ), 201


@app.route("/api/inquiries/<int:inquiry_id>/status", methods=["PATCH"])
@admin_api_required
def update_inquiry_status(inquiry_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON形式のリクエスト本文を指定してください。"}), 400

    status = data.get("status")

    if not isinstance(status, str) or status not in VALID_STATUSES:
        return jsonify({"error": "対応状況は「未対応」または「対応済み」を指定してください。"}), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "UPDATE inquiries SET status = ? WHERE id = ?",
            (status, inquiry_id),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "問い合わせが見つかりません。"}), 404

        connection.commit()
    finally:
        connection.close()

    return jsonify({"id": inquiry_id, "status": status})


@app.route("/api/inquiries/<int:inquiry_id>", methods=["DELETE"])
@admin_api_required
def delete_inquiry(inquiry_id):
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM inquiries WHERE id = ?",
            (inquiry_id,),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "問い合わせが見つかりません。"}), 404

        connection.commit()
    finally:
        connection.close()

    return jsonify({"id": inquiry_id, "message": "問い合わせを削除しました。"})


if __name__ == "__main__":
    app.run(debug=False)
