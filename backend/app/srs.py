"""Lặp lại ngắt quãng (SM-2 rút gọn) cho từng từ."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .db import now_iso


def quality_from(correct: bool, tone_warning: bool = False) -> int:
    if not correct:
        return 1
    return 4 if tone_warning else 5


def update(db, vocab_id: int, quality: int, tone_error: bool = False) -> None:
    r = db.execute("SELECT * FROM word_mastery WHERE vocab_id=?", (vocab_id,)).fetchone()
    ease, interval, reps, lapses, correct, wrong, tone_errors = 2.5, 0.0, 0, 0, 0, 0, 0
    if r:
        ease, interval, reps, lapses = r["ease"], r["interval_days"], r["reps"], r["lapses"]
        correct, wrong, tone_errors = r["correct"], r["wrong"], r["tone_errors"]
    now = datetime.now(timezone.utc)
    if quality >= 3:
        reps += 1
        correct += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 3
        else:
            interval = round(max(interval, 1) * ease, 1)
        ease = max(1.3, ease + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        due = now + timedelta(days=interval)
    else:
        reps = 0
        lapses += 1
        wrong += 1
        interval = 0
        ease = max(1.3, ease - 0.2)
        due = now  # ôn lại ngay buổi sau
    if tone_error:
        tone_errors += 1
    db.execute(
        """INSERT INTO word_mastery(vocab_id, ease, interval_days, reps, lapses, correct, wrong, tone_errors, due_at, last_seen)
           VALUES(?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(vocab_id) DO UPDATE SET ease=excluded.ease, interval_days=excluded.interval_days, reps=excluded.reps,
             lapses=excluded.lapses, correct=excluded.correct, wrong=excluded.wrong, tone_errors=excluded.tone_errors,
             due_at=excluded.due_at, last_seen=excluded.last_seen""",
        (vocab_id, ease, interval, reps, lapses, correct, wrong, tone_errors, due.isoformat(timespec="seconds"), now_iso()),
    )


def mastery_level(row) -> str:
    if row is None or row["last_seen"] is None:
        return "new"
    if row["interval_days"] >= 7:
        return "mastered"
    if row["lapses"] > 0 and row["reps"] == 0:
        return "weak"
    return "learning"
