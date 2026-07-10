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
    highlight_score REAL,
    covered_by TEXT,                      -- comma-separated outlet names, for display
    included INTEGER,                     -- NULL = not reviewed yet, 1 = include, 0 = exclude
    editor_summary TEXT,                  -- the editor's written summary, in report style
    FOREIGN KEY (duplicate_of) REFERENCES items(id),
    FOREIGN KEY (scan_id) REFERENCES scans(id),
    UNIQUE(scan_id, url)  -- prevents duplicate rows WITHIN one scan; the same
                          -- URL legitimately appearing in a different scan
                          -- (e.g. an article still current the next day) is
                          -- fine and gets its own row for that scan
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
    unique_items INTEGER DEFAULT 0,
    source_counts TEXT                    -- JSON: {"source_name": {"collected": N, "windowed": N, "relevant": N, "unique": N}, ...}
);

CREATE INDEX IF NOT EXISTS idx_items_scan_id ON items(scan_id);
CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
"""

# Columns added after the initial release. init_db() adds these to existing
# databases that predate them, so upgrading never requires deleting your
# existing media_monitor.db.
_MIGRATION_COLUMNS = [
    ("items", "highlight_score", "REAL"),
    ("items", "covered_by", "TEXT"),
    ("items", "included", "INTEGER"),
    ("items", "editor_summary", "TEXT"),
    ("scans", "source_counts", "TEXT"),
]


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
        _run_migrations(conn)
        _fix_unique_constraint_if_needed(conn)


def _run_migrations(conn):
    for table, column, col_type in _MIGRATION_COLUMNS:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _fix_unique_constraint_if_needed(conn):
    """
    Databases created before this fix have a global UNIQUE(url) constraint
    on items, which silently drops an item from a NEW scan if that same
    URL was ever stored under a different scan_id before -- the cause of
    "diagnostics say 1 item, review page shows 0" reports. SQLite can't
    ALTER a constraint directly, so this detects the old schema and
    rebuilds the table with the corrected UNIQUE(scan_id, url) constraint,
    preserving all existing data. Runs once; a no-op on databases that
    already have the fix (checked via the CREATE TABLE SQL stored by
    SQLite itself, not a version flag, so it's self-verifying).
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'items'"
    ).fetchone()
    if row is None:
        return
    create_sql = row[0]
    if "UNIQUE(scan_id, url)" in create_sql:
        return  # already fixed
    if "UNIQUE(url)" not in create_sql:
        return  # unrecognized schema shape -- don't touch it

    conn.execute("ALTER TABLE items RENAME TO items_old_unique_url")
    conn.execute(SCHEMA.split("CREATE TABLE IF NOT EXISTS scans")[0])  # (re)creates items with the fixed constraint
    columns = [r[1] for r in conn.execute("PRAGMA table_info(items)").fetchall()]
    col_list = ", ".join(columns)
    conn.execute(f"INSERT INTO items ({col_list}) SELECT {col_list} FROM items_old_unique_url")
    conn.execute("DROP TABLE items_old_unique_url")


def start_scan(mode, window_start, window_end, started_at, db_path=None):
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO scans (mode, window_start, window_end, started_at) VALUES (?, ?, ?, ?)",
            (mode, window_start, window_end, started_at),
        )
        return cur.lastrowid


def finish_scan(scan_id, finished_at, raw_items, relevant_items, unique_items, source_counts=None, db_path=None):
    import json
    with get_connection(db_path) as conn:
        source_counts_json = json.dumps(source_counts) if source_counts else None
        conn.execute(
            """UPDATE scans
               SET finished_at = ?, raw_items_collected = ?, relevant_items = ?, unique_items = ?, source_counts = ?
               WHERE id = ?""",
            (finished_at, raw_items, relevant_items, unique_items, source_counts_json, scan_id),
        )


def insert_item(item, scan_id, db_path=None):
    """
    item: dict with keys source_name, source_category, title, url, language,
    published_at, matched_keywords (list), snippet, highlight_score (optional),
    covered_by (optional list).

    Returns the new item's id, or None if the URL already existed (so we
    don't store the same article twice across scans).
    """
    with get_connection(db_path) as conn:
        try:
            cur = conn.execute(
                """INSERT INTO items
                   (source_name, source_category, title, url, language, published_at,
                    fetched_at, matched_keywords, snippet, scan_id, highlight_score, covered_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    item.get("highlight_score"),
                    ",".join(item.get("covered_by", [])) or None,
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


def get_included_items(scan_id, db_path=None):
    """Items an editor has marked included=1 for this scan, ordered by
    highlight_score descending -- exactly what belongs in the generated report."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM items WHERE scan_id = ? AND included = 1 ORDER BY highlight_score DESC",
            (scan_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_scan(scan_id, db_path=None):
    import json
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if not row:
            return None
        scan_dict = dict(row)
        # Parse source_counts JSON if present
        if scan_dict.get("source_counts"):
            try:
                scan_dict["source_counts"] = json.loads(scan_dict["source_counts"])
            except (json.JSONDecodeError, TypeError):
                scan_dict["source_counts"] = {}
        return scan_dict


def list_scans(db_path=None):
    """Most recent scans first, for the web app's landing page."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM scans ORDER BY started_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_item_review(item_id, included, editor_summary, db_path=None):
    """Save an editor's decision (include/exclude) and written summary for
    one item. `included` should be 1, 0, or None."""
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE items SET included = ?, editor_summary = ? WHERE id = ?",
            (included, editor_summary, item_id),
        )


def delete_scan(scan_id, db_path=None):
    """Deletes one scan and all of its items. Returns True if a scan was
    actually deleted, False if no scan with that id existed."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM items WHERE scan_id = ?", (scan_id,))
        cur = conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        return cur.rowcount > 0


def delete_all_scans(db_path=None):
    """Deletes every scan and every item -- a full reset. Returns the
    number of scans that were deleted."""
    with get_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM scans")
        return count
