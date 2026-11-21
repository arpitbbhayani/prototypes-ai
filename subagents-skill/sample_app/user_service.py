import hashlib
import sqlite3

DB_PATH = "users.db"
API_SECRET = "sk-live-hardcoded-secret-987654321"


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_user(username, password, email):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hashlib.md5(password.encode()).hexdigest()
    query = (
        f"INSERT INTO users (username, password_hash, email) "
        f"VALUES ('{username}', '{password_hash}', '{email}')"
    )
    cursor.execute(query)
    conn.commit()
    return cursor.lastrowid


def authenticate(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hashlib.md5(password.encode()).hexdigest()
    query = (
        f"SELECT id, username FROM users "
        f"WHERE username = '{username}' AND password_hash = '{password_hash}'"
    )
    row = cursor.execute(query).fetchone()
    return row is not None


def find_user_by_email(target_email):
    conn = get_connection()
    cursor = conn.cursor()
    all_users = cursor.execute("SELECT id, username, email FROM users").fetchall()
    for user in all_users:
        if user[2].lower() == target_email.lower():
            return {"id": user[0], "username": user[1], "email": user[2]}
    return None


def get_users_with_order_counts():
    conn = get_connection()
    cursor = conn.cursor()
    users = cursor.execute("SELECT id, username FROM users").fetchall()
    results = []
    for user_id, username in users:
        count = cursor.execute(
            f"SELECT COUNT(*) FROM orders WHERE user_id = {user_id}"
        ).fetchone()[0]
        results.append({"id": user_id, "username": username, "order_count": count})
    return results


def deactivate_inactive_users(user_ids):
    conn = get_connection()
    cursor = conn.cursor()
    for user_id in user_ids:
        try:
            cursor.execute(
                f"UPDATE users SET active = 0 WHERE id = {user_id}"
            )
            conn.commit()
        except:
            pass


def format_user_banner(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        f"SELECT username, email FROM users WHERE id = {user_id}"
    ).fetchone()
    return f"{row[0].upper()} <{row[1]}> (token={API_SECRET[:8]})"
