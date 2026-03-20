import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "data/dolby.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            chat_id   INTEGER NOT NULL,
            branch_no TEXT NOT NULL,
            PRIMARY KEY (chat_id, branch_no)
        );
        CREATE TABLE IF NOT EXISTS notified (
            branch_no TEXT NOT NULL,
            play_date TEXT NOT NULL,
            PRIMARY KEY (branch_no, play_date)
        );
    """)
    conn.commit()
    conn.close()


def add_subscription(chat_id, branch_no):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO subscriptions (chat_id, branch_no) VALUES (?, ?)",
        (chat_id, branch_no)
    )
    conn.commit()
    conn.close()


def remove_subscription(chat_id, branch_no):
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM subscriptions WHERE chat_id = ? AND branch_no = ?",
        (chat_id, branch_no)
    )
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted > 0


def get_user_branches(chat_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT branch_no FROM subscriptions WHERE chat_id = ?", (chat_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_subscribers_for_branch(branch_no):
    conn = get_conn()
    rows = conn.execute(
        "SELECT chat_id FROM subscriptions WHERE branch_no = ?", (branch_no,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_monitored_branches():
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT branch_no FROM subscriptions"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def is_notified(branch_no, play_date):
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM notified WHERE branch_no = ? AND play_date = ?",
        (branch_no, play_date)
    ).fetchone()
    conn.close()
    return row is not None


def mark_notified(branch_no, play_date):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO notified (branch_no, play_date) VALUES (?, ?)",
        (branch_no, play_date)
    )
    conn.commit()
    conn.close()
