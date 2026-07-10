"""
SQLite storage layer for the Rwanda Health Media Scanning System.

No server required -- the whole database is a single file (config.DB_PATH).
"""

import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    source_category TEXT NOT NULL,       -- local_online | international | research
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    language TEXT,
    published_at TEXT,                   -- ISO 8601 string, may be NULL if unknown
    fetched_at TEXT NOT NULL,             -- ISO 8601 string, when we collected it
    matched_keywords TEXT,                -- comma-separated
    snippet TEXT,
    duplicate_of INTEGER,                 -- FK to items.id, NULL if not a duplicate
    scan_id INTEGER NOT NULL,
    FOREIGN KEY (duplicate_of) REFERENCES items(id),
    FOREIGN KEY (scan_id) REFERENCES scans(id),
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,                   -- daily | weekly
    window_start TEXT NOT NULL,           -- ISO 8601
    window_end TEXT NOT NULL,             -- ISO 8601
    started_at TEXT NOT NULL,
    finished_at TEXT,
    raw_items_collected INTEGER DEFAULT 0,
    relevant_items INTEGER DEFAULT 0,
    unique_items INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_scan_id ON items(scan_id);
CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
"""


@contextmanager
def get_connection(db_path=None):
    conn = sqlite3.connect(db_path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path=None):
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def start_scan(mode, window_start, window_end, started_at, db_path=None):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO scans (mode, window_start, window_end, started_at) VALUES (?, ?, ?, ?)",
            (mode, window_start, window_end, started_at),
        )
        return cur.lastrowid


def finish_scan(scan_id, finished_at, raw_items, relevant_items, unique_items, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE scans
               SET finished_at = ?, raw_items_collected = ?, relevant_items = ?, unique_items = ?
               WHERE id = ?""",
            (finished_at, raw_items, relevant_items, unique_items, scan_id),
        )


def insert_item(item, scan_id, db_path=None):
    """
    item: dict with keys source_name, source_category, title, url, language,
    published_at, matched_keywords (list), snippet.

    Returns the new item's id, or None if the URL already existed (so we
    don't store the same article twice across scans).
    """
    with get_connection(db_path) as conn:
        try:
            cur = conn.execute(
                """INSERT INTO items
                   (source_name, source_category, title, url, language, published_at,
                    fetched_at, matched_keywords, snippet, scan_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["source_name"],
                    item["source_category"],
                    item["title"],
                    item["url"],
                    item.get("language"),
                    item.get("published_at"),
                    item["fetched_at"],
                    ",".join(item.get("matched_keywords", [])),
                    item.get("snippet", ""),
                    scan_id,
                ),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # URL already exists from a previous scan -- not an error.
            return None


def mark_duplicate(item_id, duplicate_of_id, db_path=None):
    with get_connection(db_path) as conn:
        conn.execute("UPDATE items SET duplicate_of = ? WHERE id = ?", (duplicate_of_id, item_id))


def get_items_for_scan(scan_id, db_path=None):
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM items WHERE scan_id = ? ORDER BY source_category, published_at DESC", (scan_id,)).fetchall()
        return [dict(r) for r in rows]


def get_scan(scan_id, db_path=None):
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        return dict(row) if row else None
