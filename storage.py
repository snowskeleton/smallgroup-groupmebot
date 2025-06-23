import sqlite3

DB_PATH = "messages.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            created_at INTEGER,
            group_id TEXT,
            sender_id TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_message(message_id: str, created_at: int, group_id: str, sender_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO messages (id, created_at, group_id, sender_id)
        VALUES (?, ?, ?, ?)
    """, (message_id, created_at, group_id, sender_id))
    conn.commit()
    conn.close()


def get_all_messages() -> list[tuple[str, int, str, str]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at, group_id, sender_id FROM messages")
    rows = c.fetchall()
    conn.close()
    return rows


def clear_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()


def save_token(token: str):
    print(token)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY,
            token TEXT
        )
    """)
    c.execute(
        "INSERT OR REPLACE INTO credentials (id, token) VALUES (1, ?)", (token,))
    conn.commit()
    conn.close()


def get_token() -> str | None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token FROM credentials WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
