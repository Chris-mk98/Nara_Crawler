import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "nara_crawler.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS job_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            recipient_email TEXT,
            keywords TEXT NOT NULL DEFAULT '[]',
            date_range_type TEXT NOT NULL DEFAULT 'relative',
            relative_days INTEGER NOT NULL DEFAULT 7,
            custom_start_date TEXT,
            custom_end_date TEXT,
            schedule_type TEXT NOT NULL DEFAULT 'disabled',
            schedule_hour INTEGER NOT NULL DEFAULT 9,
            schedule_minute INTEGER NOT NULL DEFAULT 0,
            schedule_day_of_week INTEGER,
            is_active INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS job_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            config_id INTEGER REFERENCES job_configs(id),
            status TEXT NOT NULL DEFAULT 'running',
            started_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            completed_at TEXT,
            error_message TEXT,
            excel_filename TEXT,
            row_count INTEGER,
            from_date TEXT,
            to_date TEXT,
            keywords TEXT
        );
    """)
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(email: str, password_hash: str):
    conn = get_conn()
    conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row)


def get_config_by_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM job_configs WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_config(user_id: int, recipient_email: str, keywords: list,
                date_range_type: str, relative_days: int,
                custom_start_date: str, custom_end_date: str,
                schedule_type: str, schedule_hour: int, schedule_minute: int,
                schedule_day_of_week: int, is_active: bool):
    conn = get_conn()
    keywords_json = json.dumps(keywords, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = conn.execute(
        "SELECT id FROM job_configs WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE job_configs SET
                recipient_email = ?, keywords = ?, date_range_type = ?,
                relative_days = ?, custom_start_date = ?, custom_end_date = ?,
                schedule_type = ?, schedule_hour = ?, schedule_minute = ?,
                schedule_day_of_week = ?, is_active = ?, updated_at = ?
            WHERE user_id = ?
        """, (recipient_email, keywords_json, date_range_type, relative_days,
              custom_start_date, custom_end_date, schedule_type, schedule_hour,
              schedule_minute, schedule_day_of_week, 1 if is_active else 0, now, user_id))
    else:
        conn.execute("""
            INSERT INTO job_configs (
                user_id, recipient_email, keywords, date_range_type, relative_days,
                custom_start_date, custom_end_date, schedule_type, schedule_hour,
                schedule_minute, schedule_day_of_week, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, recipient_email, keywords_json, date_range_type, relative_days,
              custom_start_date, custom_end_date, schedule_type, schedule_hour,
              schedule_minute, schedule_day_of_week, 1 if is_active else 0, now, now))

    conn.commit()
    row = conn.execute("SELECT * FROM job_configs WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def get_all_active_configs():
    conn = get_conn()
    rows = conn.execute("""
        SELECT jc.* FROM job_configs jc
        WHERE jc.is_active = 1 AND jc.schedule_type != 'disabled'
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_job_history(user_id: int, config_id: int):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO job_history (user_id, config_id, status, started_at)
        VALUES (?, ?, 'running', ?)
    """, (user_id, config_id, now))
    conn.commit()
    history_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = conn.execute("SELECT * FROM job_history WHERE id = ?", (history_id,)).fetchone()
    conn.close()
    return dict(row)


def update_job_history(history_id: int, status: str, excel_filename: str = None,
                       row_count: int = None, error_message: str = None,
                       from_date: str = None, to_date: str = None,
                       keywords_json: str = None):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE job_history SET
            status = ?, completed_at = ?, excel_filename = ?, row_count = ?,
            error_message = ?, from_date = ?, to_date = ?, keywords = ?
        WHERE id = ?
    """, (status, now, excel_filename, row_count, error_message,
          from_date, to_date, keywords_json, history_id))
    conn.commit()
    conn.close()


def get_job_history(user_id: int, limit: int = 20, job_id: int = None):
    conn = get_conn()
    if job_id is not None:
        rows = conn.execute(
            "SELECT * FROM job_history WHERE user_id = ? AND id = ?",
            (user_id, job_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM job_history WHERE user_id = ? ORDER BY started_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
