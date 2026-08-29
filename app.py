import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request


app = Flask(__name__, instance_relative_config=True)
DATABASE_PATH = Path(app.instance_path) / "inquiries.db"
STATUS_OPEN = "未対応"


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/inquiries", methods=["GET"])
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


if __name__ == "__main__":
    app.run(debug=True)
