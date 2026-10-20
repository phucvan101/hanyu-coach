"""Luyện riêng: nhìn Hán tự → gõ pinyin (ngoài luồng buổi học)."""
from __future__ import annotations

import random

from . import quiz, srs
from .chengyu import CHENGYU
from .pinyin_utils import expected_forms
from .db import now_iso, row_to_dict, rows_to_dicts

SCOPES = ("all", "book", "unit", "weak", "due", "tones")

_BASE = """SELECT v.id, v.hanzi, v.pinyin, v.primary_meaning, v.han_viet, v.usage_vi, v.example_zh, v.example_vi,
                  v.unit_id, m.reps, m.lapses, m.wrong, m.tone_errors, m.due_at, m.last_seen
           FROM vocab v JOIN books b ON b.id=v.book_id LEFT JOIN word_mastery m ON m.vocab_id=v.id
           WHERE b.status='ready' AND v.unit_id IS NOT NULL"""


def options(db) -> dict:
    books = rows_to_dicts(db.execute("SELECT id, title FROM books WHERE status='ready' ORDER BY id").fetchall())
    for b in books:
        b["units"] = rows_to_dicts(db.execute(
            "SELECT u.id, u.idx, u.title_vi, u.title_zh, COUNT(v.id) word_count FROM units u "
            "LEFT JOIN vocab v ON v.unit_id=u.id WHERE u.book_id=? GROUP BY u.id ORDER BY u.idx", (b["id"],)
        ).fetchall())
        b["word_count"] = sum(u["word_count"] for u in b["units"])
    words = rows_to_dicts(db.execute(_BASE).fetchall())
    now = now_iso()
    return {
        "books": books,
        "counts": {
            "all": len(words),
            "weak": sum(1 for w in words if _is_weak(w)),
            "due": sum(1 for w in words if w["due_at"] and w["due_at"] <= now),
            "tones": sum(1 for w in words if (w["tone_errors"] or 0) > 0),
        },
    }


def _is_weak(w) -> bool:
    return bool(w["last_seen"]) and (w["lapses"] or 0) > 0 and (w["reps"] or 0) == 0


def _priority(w, now: str) -> int:
    """Nhỏ hơn = ưu tiên hơn: từ yếu → đến hạn → chưa học → còn lại."""
    if _is_weak(w):
        return 0
    if w["due_at"] and w["due_at"] <= now:
        return 1
    if not w["last_seen"]:
        return 2
    return 3


def deck(db, scope: str, ref_id: int | None, limit: int, full: bool = False) -> list[dict]:
    if scope not in SCOPES:
        scope = "all"
    q, args = _BASE, []
    if scope == "book" and ref_id:
        q += " AND v.book_id=?"
        args.append(ref_id)
    elif scope == "unit" and ref_id:
        q += " AND v.unit_id=?"
        args.append(ref_id)
    words = rows_to_dicts(db.execute(q, args).fetchall())
    now = now_iso()
    if scope == "weak":
        words = [w for w in words if _is_weak(w)]
    elif scope == "due":
        words = [w for w in words if w["due_at"] and w["due_at"] <= now]
    elif scope == "tones":
        words = [w for w in words if (w["tone_errors"] or 0) > 0]
    # cùng một chữ Hán có thể nằm ở nhiều quyển
    seen, uniq = set(), []
    random.shuffle(words)
    for w in words:
        if w["hanzi"] not in seen:
            seen.add(w["hanzi"])
            uniq.append(w)
    # bài/quyển cụ thể: lấy hết theo thứ tự ngẫu nhiên; phạm vi rộng: ưu tiên từ cần ôn
    if scope in ("all", "book"):
        uniq.sort(key=lambda w: _priority(w, now))
    if limit > 0:
        uniq = uniq[:limit]
        random.shuffle(uniq)
    if full:  # flashcard cần cả mặt sau của thẻ
        return [{"vocab_id": w["id"], "hanzi": w["hanzi"], "pinyin": w["pinyin"], "meaning": w["primary_meaning"],
                 "han_viet": w["han_viet"], "usage": w["usage_vi"], "example_zh": w["example_zh"],
                 "example_vi": w["example_vi"]} for w in uniq]
    return [{"vocab_id": w["id"], "hanzi": w["hanzi"], "meaning": w["primary_meaning"], "han_viet": w["han_viet"]}
            for w in uniq]


def check(db, vocab_id: int, user_answer: str, record: bool = True) -> dict:
    w = row_to_dict(db.execute("SELECT * FROM vocab WHERE id=?", (vocab_id,)).fetchone())
    if not w:
        raise LookupError("Không tìm thấy từ")
    reveal = {
        "hanzi": w["hanzi"], "pinyin": w["pinyin"], "meaning": w["primary_meaning"], "han_viet": w["han_viet"],
        "usage": w["usage_vi"], "example_zh": w["example_zh"], "example_vi": w["example_vi"],
    }
    g = quiz.grade("hanzi_pinyin", {"value": w["pinyin"]}, w["hanzi"], user_answer)
    if record:
        srs.update(db, vocab_id, srs.quality_from(g["correct"], bool(g["tone_warning"])),
                   tone_error=g["tone_warning"] == "mismatch")
    return {**g, "answer": reveal}


# flashcard: tự chấm 4 mức kiểu Anki -> chất lượng SM-2
RATINGS = {1: 1, 2: 3, 3: 4, 4: 5}  # Quên · Khó · Nhớ · Dễ


def rate(db, vocab_id: int, rating: int) -> dict:
    if rating not in RATINGS:
        raise ValueError("Mức chấm phải từ 1 đến 4")
    if not db.execute("SELECT 1 FROM vocab WHERE id=?", (vocab_id,)).fetchone():
        raise LookupError("Không tìm thấy từ")
    srs.update(db, vocab_id, RATINGS[rating])
    m = row_to_dict(db.execute("SELECT interval_days, due_at FROM word_mastery WHERE vocab_id=?", (vocab_id,)).fetchone())
    return {"interval_days": m["interval_days"], "due_at": m["due_at"]}


# game bắn chữ: gõ pinyin không dấu để hạ chữ Hán
def _keys(hanzi: str, pinyin: str) -> list[str]:
    # mọi cách viết pinyin chấp nhận được (dữ liệu file + pypinyin), chỉ giữ chữ cái
    return [k for k in dict.fromkeys("".join(s for s, _ in f) for f in expected_forms(hanzi, pinyin)) if k]


def game_deck(db, scope: str, ref_id: int | None) -> list[dict]:
    out = []
    for c in deck(db, scope, ref_id, 0, full=True):
        keys = _keys(c["hanzi"], c["pinyin"])
        if keys:
            out.append({"vocab_id": c["vocab_id"], "hanzi": c["hanzi"], "pinyin": c["pinyin"],
                        "meaning": c["meaning"], "han_viet": c["han_viet"], "keys": keys})
    return out


def game_bosses(db, scope: str, ref_id: int | None) -> list[dict]:
    """Boss: cụm từ dài (>= 4 chữ) trong kho của người học trước, sau đó là thành ngữ có sẵn."""
    own = [c for c in game_deck(db, scope, ref_id) if len(c["hanzi"]) >= 4]
    seen = {c["hanzi"] for c in own}
    built = []
    for hanzi, py, hv, meaning in CHENGYU:
        if hanzi in seen:
            continue
        keys = _keys(hanzi, py)
        if keys:
            built.append({"vocab_id": None, "hanzi": hanzi, "pinyin": py, "meaning": meaning, "han_viet": hv, "keys": keys})
    random.shuffle(own)
    random.shuffle(built)
    return own + built


# hạ gọn không gõ sai -> nhớ; hạ nhưng có gõ sai/nhờ gợi ý -> khó; để lọt -> quên
GAME_QUALITY = {"clean": 4, "rough": 3, "miss": 1}


def game_results(db, results: list) -> dict:
    n = 0
    for r in results[:500]:
        q = GAME_QUALITY.get(str(r.get("result")))
        vid = r.get("vocab_id")
        if q is None or not isinstance(vid, int):
            continue
        if db.execute("SELECT 1 FROM vocab WHERE id=?", (vid,)).fetchone():
            srs.update(db, vid, q)
            n += 1
    return {"recorded": n}
