"""
database.py - Simple SQLite persistence layer for the bot.
Stores: warns, filters, locks, welcome messages, antiflood settings.
"""
import sqlite3
import threading
import json

DB_PATH = "botdata.db"
_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            reasons TEXT DEFAULT '[]',
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            warn_limit INTEGER DEFAULT 3,
            welcome_text TEXT DEFAULT 'Welcome {mention} to {chatname}!',
            welcome_enabled INTEGER DEFAULT 1,
            goodbye_text TEXT DEFAULT '{mention} has left the group.',
            goodbye_enabled INTEGER DEFAULT 0,
            flood_limit INTEGER DEFAULT 0,
            locks TEXT DEFAULT '{}',
            rules_text TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            chat_id INTEGER,
            keyword TEXT,
            reply_text TEXT,
            PRIMARY KEY (chat_id, keyword)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            chat_id INTEGER,
            name TEXT,
            content TEXT,
            PRIMARY KEY (chat_id, name)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            chat_id INTEGER,
            word TEXT,
            PRIMARY KEY (chat_id, word)
        )
    """)

    conn.commit()
    conn.close()


# ---------- Warns ----------

def add_warn(chat_id, user_id, reason=""):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count, reasons FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        row = cur.fetchone()
        if row:
            reasons = json.loads(row["reasons"])
            reasons.append(reason)
            count = row["count"] + 1
            cur.execute("UPDATE warns SET count=?, reasons=? WHERE chat_id=? AND user_id=?",
                        (count, json.dumps(reasons), chat_id, user_id))
        else:
            count = 1
            cur.execute("INSERT INTO warns (chat_id, user_id, count, reasons) VALUES (?, ?, ?, ?)",
                        (chat_id, user_id, count, json.dumps([reason])))
        conn.commit()
        conn.close()
        return count


def reset_warns(chat_id, user_id):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        conn.commit()
        conn.close()


def get_warns(chat_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT count, reasons FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["count"], json.loads(row["reasons"])
    return 0, []


# ---------- Chat settings ----------

def get_chat_settings(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_settings WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    if not row:
        conn.execute("INSERT INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        cur.execute("SELECT * FROM chat_settings WHERE chat_id=?", (chat_id,))
        row = cur.fetchone()
    conn.close()
    return dict(row)


def update_chat_settings(chat_id, **kwargs):
    get_chat_settings(chat_id)  # ensure row exists
    with _lock:
        conn = get_conn()
        cols = ", ".join(f"{k}=?" for k in kwargs)
        values = list(kwargs.values()) + [chat_id]
        conn.execute(f"UPDATE chat_settings SET {cols} WHERE chat_id=?", values)
        conn.commit()
        conn.close()


def get_locks(chat_id):
    settings = get_chat_settings(chat_id)
    return json.loads(settings["locks"])


def set_lock(chat_id, lock_type, enabled):
    locks = get_locks(chat_id)
    locks[lock_type] = enabled
    update_chat_settings(chat_id, locks=json.dumps(locks))


# ---------- Filters ----------

def add_filter(chat_id, keyword, reply_text):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO filters (chat_id, keyword, reply_text) VALUES (?, ?, ?)",
            (chat_id, keyword.lower(), reply_text)
        )
        conn.commit()
        conn.close()


def remove_filter(chat_id, keyword):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, keyword.lower()))
        conn.commit()
        conn.close()


def get_filters(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT keyword, reply_text FROM filters WHERE chat_id=?", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return {r["keyword"]: r["reply_text"] for r in rows}


# ---------- Notes ----------

def add_note(chat_id, name, content):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO notes (chat_id, name, content) VALUES (?, ?, ?)",
            (chat_id, name.lower(), content)
        )
        conn.commit()
        conn.close()


def get_note(chat_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT content FROM notes WHERE chat_id=? AND name=?", (chat_id, name.lower()))
    row = cur.fetchone()
    conn.close()
    return row["content"] if row else None


def remove_note(chat_id, name):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM notes WHERE chat_id=? AND name=?", (chat_id, name.lower()))
        conn.commit()
        conn.close()


def get_all_notes(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM notes WHERE chat_id=?", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


# ---------- Blacklist words ----------

def add_blacklist_word(chat_id, word):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO blacklist (chat_id, word) VALUES (?, ?)",
            (chat_id, word.lower())
        )
        conn.commit()
        conn.close()


def remove_blacklist_word(chat_id, word):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM blacklist WHERE chat_id=? AND word=?", (chat_id, word.lower()))
        conn.commit()
        conn.close()


def get_blacklist_words(chat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT word FROM blacklist WHERE chat_id=?", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return [r["word"] for r in rows]
