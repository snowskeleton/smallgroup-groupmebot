from sqlite3 import connect
from time import time

from config import DB_PATH
from exceptions import NoGroupID, NoSheetLink, NoAuthenticationToken

def init_db():
    conn = connect(DB_PATH)
    print("[DEBUG] Running init_db()")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            created_at INTEGER,
            group_id TEXT,
            sender_id TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY,
            token TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            created_at INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            token TEXT UNIQUE,
            created_at INTEGER,
            used INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT UNIQUE,
            created_at INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            level TEXT,
            source TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_message(message_id: str, created_at: int, group_id: str, sender_id: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO messages (id, created_at, group_id, sender_id)
        VALUES (?, ?, ?, ?)
    """, (message_id, created_at, group_id, sender_id))
    conn.commit()
    conn.close()


def get_all_messages() -> list[tuple[str, int, str, str]]:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at, group_id, sender_id FROM messages")
    rows = c.fetchall()
    conn.close()
    return rows


def clear_messages():
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


def save_token(token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO credentials (id, token) VALUES (1, ?)", (token,))
    conn.commit()
    conn.close()


def get_token() -> str:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token FROM credentials WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if not row:
        raise NoAuthenticationToken(
            "Please authenticate with '/authenticate' first")
    return row[0]


def save_schedule(schedule: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('schedule', ?)", (schedule,))
    conn.commit()
    conn.close()


def get_schedule() -> str | None:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'schedule'")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def save_sheet_link(link: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('link', ?)", (link,))
    conn.commit()
    conn.close()


def get_sheet_link() -> str:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'link'")
    row = c.fetchone()
    conn.close()
    if not row:
        raise NoSheetLink(
            "Please add a sheet link with /schedule link <google sheet link>")
    return row[0]


def save_group_id(group_id: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('group_id', ?)", (group_id,))
    conn.commit()
    conn.close()


def get_group_id() -> str:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'group_id'")
    row = c.fetchone()
    conn.close()
    if not row:
        raise NoGroupID("I don't know what group I'm in :(")
    return row[0]


# --- Dashboard Users ---

def create_user(email: str) -> int:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO dashboard_users (email, created_at) VALUES (?, ?)",
              (email, int(time())))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, created_at FROM dashboard_users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, created_at FROM dashboard_users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, created_at FROM dashboard_users ORDER BY created_at")
    rows = c.fetchall()
    conn.close()
    return rows


def user_count() -> int:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dashboard_users")
    count = c.fetchone()[0]
    conn.close()
    return count


def delete_user(user_id: int):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM dashboard_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# --- Login Tokens ---

def create_login_token(email: str, token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO login_tokens (email, token, created_at) VALUES (?, ?, ?)",
              (email, token, int(time())))
    conn.commit()
    conn.close()


def get_login_token(token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, email, token, created_at, used FROM login_tokens WHERE token = ? AND used = 0",
              (token,))
    row = c.fetchone()
    conn.close()
    return row


def mark_token_used(token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE login_tokens SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# --- Sessions ---

def create_session(user_id: int, token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (user_id, token, created_at) VALUES (?, ?, ?)",
              (user_id, token, int(time())))
    conn.commit()
    conn.close()


def get_session(token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, token, created_at FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    return row


def delete_session(token: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# --- Logs ---

def insert_log(timestamp: int, level: str, source: str, message: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, level, source, message) VALUES (?, ?, ?, ?)",
              (timestamp, level, source, message))
    # Keep only the last 1000 entries
    c.execute("""
        DELETE FROM logs WHERE id NOT IN (
            SELECT id FROM logs ORDER BY id DESC LIMIT 1000
        )
    """)
    conn.commit()
    conn.close()


def get_logs(level: str = None, limit: int = 100) -> list:
    conn = connect(DB_PATH)
    c = conn.cursor()
    if level:
        c.execute("SELECT id, timestamp, level, source, message FROM logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                  (level, limit))
    else:
        c.execute("SELECT id, timestamp, level, source, message FROM logs ORDER BY id DESC LIMIT ?",
                  (limit,))
    rows = c.fetchall()
    conn.close()
    return rows
