import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_file TEXT,
    status TEXT NOT NULL DEFAULT 'importing',   -- importing | ready | error
    status_msg TEXT,
    grouped_by TEXT,                             -- llm | fallback
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    title_vi TEXT NOT NULL,
    title_zh TEXT,
    scenario_vi TEXT,
    ai_role_vi TEXT,
    user_role_vi TEXT
);

CREATE TABLE IF NOT EXISTS vocab (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
    hanzi TEXT NOT NULL,
    pinyin TEXT NOT NULL,
    han_viet TEXT,
    meanings TEXT NOT NULL,          -- JSON array
    primary_meaning TEXT,
    is_function_word INTEGER NOT NULL DEFAULT 0,
    usage_vi TEXT,
    example_zh TEXT,
    example_vi TEXT,
    enriched INTEGER NOT NULL DEFAULT 0,
    UNIQUE(book_id, hanzi)
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',  -- processing | ready | error
    status_msg TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grammar_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    material_id INTEGER REFERENCES materials(id) ON DELETE CASCADE,
    pattern TEXT NOT NULL,
    explanation_vi TEXT,
    example_zh TEXT,
    example_vi TEXT
);

CREATE TABLE IF NOT EXISTS unit_progress (
    unit_id INTEGER PRIMARY KEY REFERENCES units(id) ON DELETE CASCADE,
    vocab_best INTEGER NOT NULL DEFAULT 0,
    controlled_best INTEGER NOT NULL DEFAULT 0,
    free_best INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS word_mastery (
    vocab_id INTEGER PRIMARY KEY REFERENCES vocab(id) ON DELETE CASCADE,
    ease REAL NOT NULL DEFAULT 2.5,
    interval_days REAL NOT NULL DEFAULT 0,
    reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    wrong INTEGER NOT NULL DEFAULT 0,
    tone_errors INTEGER NOT NULL DEFAULT 0,
    due_at TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
    start_stage TEXT NOT NULL,          -- vocab | controlled | free
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    quiz_score INTEGER,
    skill_scores TEXT,                   -- JSON
    report TEXT                          -- JSON
);

CREATE TABLE IF NOT EXISTS quiz_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,                  -- review | quiz
    order_idx INTEGER NOT NULL,
    vocab_id INTEGER REFERENCES vocab(id) ON DELETE CASCADE,
    qtype TEXT NOT NULL,
    payload TEXT NOT NULL,               -- JSON (prompt, options...) gửi cho FE
    answer TEXT NOT NULL,                -- JSON đáp án đúng (không gửi trước khi trả lời)
    user_answer TEXT,
    correct INTEGER,
    tone_warning TEXT,
    feedback TEXT,
    answered_at TEXT
);

CREATE TABLE IF NOT EXISTS convos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
    stage TEXT NOT NULL,                 -- controlled | free
    intro_vi TEXT,
    max_turns INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    score INTEGER,
    target_words TEXT,                   -- JSON list hanzi
    used_words TEXT,                     -- JSON list hanzi
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    convo_id INTEGER NOT NULL REFERENCES convos(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    role TEXT NOT NULL,                  -- ai | user
    input_mode TEXT,                     -- hanzi | pinyin | voice
    raw_text TEXT,
    hanzi TEXT,
    pinyin TEXT,
    vi TEXT,
    eval TEXT,                           -- JSON
    score INTEGER,
    out_of_vocab TEXT,                   -- JSON list
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    turn_id INTEGER REFERENCES turns(id) ON DELETE SET NULL,
    original TEXT NOT NULL,
    corrected TEXT NOT NULL,
    error_type TEXT,
    grammar_point TEXT,
    explanation_vi TEXT,
    resolved INTEGER NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    correct_reviews INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sentence_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    error_id INTEGER NOT NULL REFERENCES errors(id) ON DELETE CASCADE,
    order_idx INTEGER NOT NULL,
    user_answer TEXT,
    correct INTEGER,
    feedback TEXT,
    answered_at TEXT
);

-- lộ trình cải thiện sinh ra sau buổi hội thoại tổng hợp
CREATE TABLE IF NOT EXISTS plan_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    kind TEXT NOT NULL,                  -- pinyin_drill | rewrite | grammar_convo | words_convo
    title_vi TEXT NOT NULL,
    detail_vi TEXT,
    payload TEXT NOT NULL,               -- JSON
    status TEXT NOT NULL DEFAULT 'open', -- open | done
    score INTEGER,
    run_session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    done_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_vocab_unit ON vocab(unit_id);
CREATE INDEX IF NOT EXISTS idx_quiz_session ON quiz_items(session_id);
CREATE INDEX IF NOT EXISTS idx_turns_convo ON turns(convo_id);
CREATE INDEX IF NOT EXISTS idx_errors_resolved ON errors(resolved);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# cột thêm sau phiên bản đầu (DB cũ cần ALTER)
MIGRATIONS = {
    "sessions": {
        "book_id": "INTEGER REFERENCES books(id) ON DELETE SET NULL",
        "topic": "TEXT",
        "focus": "TEXT",       # JSON: trọng tâm luyện của buổi tổng hợp (ngữ pháp, từ, số lượt)
        "task_id": "INTEGER",  # buổi chạy cho một nhiệm vụ trong lộ trình
    },
    "convos": {"book_id": "INTEGER"},
    "turns": {"notes": "TEXT"},  # JSON: chú thích từ mới AI dùng ngoài vốn từ
}


def init_db() -> None:
    with get_db() as db:
        db.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}
            for col, decl in cols.items():
                if col not in have:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def row_to_dict(row, json_fields=()):
    if row is None:
        return None
    d = dict(row)
    for f in json_fields:
        if f in d and isinstance(d[f], str):
            try:
                d[f] = json.loads(d[f])
            except json.JSONDecodeError:
                pass
    return d


def rows_to_dicts(rows, json_fields=()):
    return [row_to_dict(r, json_fields) for r in rows]


def get_setting(db, key, default=None):
    r = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r and r["value"] is not None else default


def set_setting(db, key, value):
    db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
