from sqlite3 import connect

from exceptions import NoGroupID, NoSheetLink, NoAuthenticationToken


DB_PATH = "messages.db"

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
    print(token)
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO credentials (id, token) VALUES (1, ?)", (token,))
    conn.commit()
    conn.close()


def get_token() -> str | None:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT token FROM credentials WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def save_schedule(schedule: str):
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('schedule', ?)", (schedule,))
    conn.commit()
    conn.close()


def get_schedule() -> str:
    conn = connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'schedule'")
    row = c.fetchone()
    conn.close()
    if not row:
        raise NoAuthenticationToken(
            "Please authenticate with '/authenticate' first")
    return row[0]


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
