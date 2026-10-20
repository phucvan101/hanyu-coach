"""Luồng học: session → ôn tập → kiểm tra từ vựng → hội thoại có kiểm soát → hội thoại tự do → báo cáo."""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone

from . import llm, plan, prompts, quiz, srs
from .config import (CONVO_TURNS_CONTROLLED, CONVO_TURNS_FREE, PASS_THRESHOLD, QUIZ_MAX_QUESTIONS,
                     REVIEW_MAX_SENTENCES, REVIEW_MAX_WORDS)
from .db import now_iso, row_to_dict, rows_to_dicts
from .pinyin_utils import is_latin_input, to_display_pinyin
from .text_utils import build_whitelist, out_of_vocab, strip_cjk_punct, words_used

log = logging.getLogger("hanyu.learning")

STAGES = ["vocab", "controlled", "free"]
STAGE_LABEL = {"vocab": "Kiểm tra từ vựng", "controlled": "Hội thoại có kiểm soát", "free": "Hội thoại tự do",
               "book": "Hội thoại tổng hợp"}
BOOK_TURNS = (6, 8, 12, 16)
SKILL_LABEL = {
    "recognition": "Nhận diện từ",
    "pinyin": "Pinyin (âm)",
    "tones": "Thanh điệu",
    "listening": "Nghe",
    "writing": "Viết Hán tự",
    "grammar": "Ngữ pháp",
    "communication": "Giao tiếp",
    "vocab_usage": "Vận dụng từ",
}


class LearnError(Exception):
    pass


# ------------------------------------------------------------------ helpers

def vocab_pool(db) -> list[dict]:
    return rows_to_dicts(db.execute("SELECT * FROM vocab WHERE unit_id IS NOT NULL").fetchall())


def unit_words(db, unit_id: int) -> list[dict]:
    return rows_to_dicts(db.execute("SELECT * FROM vocab WHERE unit_id=? ORDER BY id", (unit_id,)).fetchall())


def book_words(db, book_id: int) -> list[dict]:
    return rows_to_dicts(db.execute("SELECT * FROM vocab WHERE book_id=? AND unit_id IS NOT NULL ORDER BY id", (book_id,)).fetchall())


def get_book(db, book_id: int) -> dict:
    b = row_to_dict(db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone())
    if not b:
        raise LearnError("Không tìm thấy quyển")
    return b


def get_unit(db, unit_id: int) -> dict:
    u = row_to_dict(db.execute("SELECT * FROM units WHERE id=?", (unit_id,)).fetchone())
    if not u:
        raise LearnError("Không tìm thấy bài học")
    return u


def get_progress(db, unit_id: int) -> dict:
    r = db.execute("SELECT * FROM unit_progress WHERE unit_id=?", (unit_id,)).fetchone()
    p = dict(r) if r else {"unit_id": unit_id, "vocab_best": 0, "controlled_best": 0, "free_best": 0}
    p["vocab_passed"] = p["vocab_best"] >= PASS_THRESHOLD
    p["controlled_passed"] = p["controlled_best"] >= PASS_THRESHOLD
    p["free_passed"] = p["free_best"] >= PASS_THRESHOLD
    p["unlocked"] = {"vocab": True, "controlled": p["vocab_passed"], "free": p["controlled_passed"]}
    return p


def _bump_progress(db, unit_id: int, field: str, score: int) -> None:
    db.execute("INSERT OR IGNORE INTO unit_progress(unit_id) VALUES(?)", (unit_id,))
    db.execute(f"UPDATE unit_progress SET {field}=MAX({field}, ?), updated_at=? WHERE unit_id=?", (score, now_iso(), unit_id))


def next_stage(p: dict) -> str:
    for s in STAGES:
        if not p[f"{s}_passed"]:
            return s
    return "free"


def recommend(db) -> dict | None:
    units = db.execute(
        "SELECT u.id FROM units u JOIN books b ON b.id=u.book_id WHERE b.status='ready' ORDER BY b.id, u.idx"
    ).fetchall()
    for u in units:
        p = get_progress(db, u["id"])
        if not (p["vocab_passed"] and p["controlled_passed"] and p["free_passed"]):
            return {"unit_id": u["id"], "stage": next_stage(p)}
    if units:
        # đã xong hết: chọn bài có nhiều từ cần ôn nhất
        r = db.execute(
            """SELECT v.unit_id, COUNT(*) c FROM word_mastery m JOIN vocab v ON v.id=m.vocab_id
               WHERE m.due_at <= ? GROUP BY v.unit_id ORDER BY c DESC LIMIT 1""", (now_iso(),)
        ).fetchone()
        uid = r["unit_id"] if r else random.choice(units)["id"]
        return {"unit_id": uid, "stage": "free"}
    return None


def _whitelist(db) -> set[str]:
    return build_whitelist([r["hanzi"] for r in db.execute("SELECT hanzi FROM vocab").fetchall()])


def _grammar_for(db, book_id: int) -> list[dict]:
    g = rows_to_dicts(db.execute("SELECT pattern, example_zh FROM grammar_points WHERE book_id=?", (book_id,)).fetchall())
    random.shuffle(g)
    return g[:15]


# ------------------------------------------------------------------ session

def create_session(db, unit_id: int | None = None, stage: str | None = None) -> int:
    if unit_id is None:
        rec = recommend(db)
        if not rec:
            raise LearnError("Chưa có dữ liệu. Hãy nhập file từ vựng trong mục Thư viện.")
        unit_id, stage = rec["unit_id"], stage or rec["stage"]
    get_unit(db, unit_id)
    p = get_progress(db, unit_id)
    stage = stage or next_stage(p)
    if stage not in STAGES:
        raise LearnError("Bước học không hợp lệ")
    if not p["unlocked"][stage]:
        raise LearnError(f"Cần đạt ≥ {PASS_THRESHOLD}% ở bước trước để mở '{STAGE_LABEL[stage]}'.")
    cur = db.execute("INSERT INTO sessions(unit_id, start_stage, started_at) VALUES(?,?,?)", (unit_id, stage, now_iso()))
    sid = cur.lastrowid

    # ôn tập đầu buổi: từ đến hạn/từ yếu (không thuộc bài đang học) + câu sai cũ
    due = rows_to_dicts(db.execute(
        """SELECT v.* FROM word_mastery m JOIN vocab v ON v.id=m.vocab_id
           WHERE m.due_at <= ? AND v.unit_id IS NOT NULL AND v.unit_id != ?
           ORDER BY m.lapses DESC, m.due_at ASC LIMIT ?""",
        (now_iso(), unit_id, REVIEW_MAX_WORDS),
    ).fetchall())
    if stage != "vocab" and len(due) < REVIEW_MAX_WORDS:
        # khi vào thẳng hội thoại, ôn nhanh cả từ yếu của chính bài
        extra = rows_to_dicts(db.execute(
            """SELECT v.* FROM word_mastery m JOIN vocab v ON v.id=m.vocab_id
               WHERE v.unit_id=? AND m.due_at <= ? ORDER BY m.lapses DESC LIMIT ?""",
            (unit_id, now_iso(), REVIEW_MAX_WORDS - len(due)),
        ).fetchall())
        due += [e for e in extra if e["id"] not in {d["id"] for d in due}]
    if due:
        quiz.insert_items(db, sid, "review", quiz.assign_types(due, None), vocab_pool(db))
    errs = db.execute(
        "SELECT id FROM errors WHERE resolved=0 ORDER BY review_count ASC, created_at DESC LIMIT ?", (REVIEW_MAX_SENTENCES,)
    ).fetchall()
    for i, e in enumerate(errs):
        db.execute("INSERT INTO sentence_reviews(session_id, error_id, order_idx) VALUES(?,?,?)", (sid, e["id"], i))
    return sid


def create_book_session(db, book_id: int, topic: str, max_turns: int = 8, focus: dict | None = None,
                        task_id: int | None = None) -> int:
    """Buổi hội thoại tổng hợp cả quyển với chủ đề người học tự chọn (không ôn tập đầu buổi)."""
    b = get_book(db, book_id)
    if b["status"] != "ready":
        raise LearnError("Quyển này chưa xử lý xong")
    topic = (topic or "").strip()[:200]
    if not topic:
        raise LearnError("Hãy nhập chủ đề muốn nói")
    focus = dict(focus or {})
    focus["max_turns"] = max_turns if max_turns in BOOK_TURNS else 8
    cur = db.execute(
        "INSERT INTO sessions(unit_id, start_stage, started_at, book_id, topic, focus, task_id) VALUES(NULL,'book',?,?,?,?,?)",
        (now_iso(), book_id, topic, json.dumps(focus, ensure_ascii=False), task_id),
    )
    return cur.lastrowid


def _item_public(r) -> dict:
    d = dict(r)
    out = {"id": d["id"], "kind": d["kind"], "order_idx": d["order_idx"], "qtype": d["qtype"],
           "payload": json.loads(d["payload"]), "answered": d["answered_at"] is not None}
    if out["answered"]:
        out.update({"user_answer": d["user_answer"], "correct": bool(d["correct"]), "tone_warning": d["tone_warning"],
                    "feedback": d["feedback"], "answer": json.loads(d["answer"])})
    return out


def _turn_public(t: dict) -> dict:
    d = dict(t)
    if isinstance(d.get("eval"), str):
        d["eval"] = json.loads(d["eval"])
    if isinstance(d.get("out_of_vocab"), str):
        d["out_of_vocab"] = json.loads(d["out_of_vocab"])
    if isinstance(d.get("notes"), str):
        d["notes"] = json.loads(d["notes"])
    return d


def convo_public(db, convo_id: int) -> dict:
    c = row_to_dict(db.execute("SELECT * FROM convos WHERE id=?", (convo_id,)).fetchone(), ("target_words", "used_words"))
    turns = [_turn_public(t) for t in rows_to_dicts(db.execute("SELECT * FROM turns WHERE convo_id=? ORDER BY idx", (convo_id,)).fetchall())]
    c["turns"] = turns
    c["user_turns"] = sum(1 for t in turns if t["role"] == "user")
    c["stage_label"] = STAGE_LABEL[c["stage"]]
    return c


def session_state(db, sid: int) -> dict:
    s = row_to_dict(db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone(), ("skill_scores", "report", "focus"))
    if not s:
        raise LearnError("Không tìm thấy buổi học")
    unit = get_unit(db, s["unit_id"]) if s["unit_id"] else None
    book = row_to_dict(db.execute("SELECT id, title FROM books WHERE id=?", (s["book_id"],)).fetchone()) if s.get("book_id") else None
    items = [_item_public(r) for r in db.execute("SELECT * FROM quiz_items WHERE session_id=? ORDER BY kind DESC, order_idx", (sid,)).fetchall()]
    srev = []
    for r in db.execute(
        """SELECT sr.*, e.original, e.corrected, e.explanation_vi, e.grammar_point, e.error_type
           FROM sentence_reviews sr JOIN errors e ON e.id=sr.error_id WHERE sr.session_id=? ORDER BY sr.order_idx""", (sid,)
    ).fetchall():
        d = dict(r)
        pub = {"id": d["id"], "error_id": d["error_id"], "original": d["original"], "grammar_point": d["grammar_point"],
               "answered": d["answered_at"] is not None}
        if pub["answered"]:
            pub.update({"user_answer": d["user_answer"], "correct": bool(d["correct"]), "feedback": d["feedback"],
                        "corrected": d["corrected"], "explanation_vi": d["explanation_vi"]})
        srev.append(pub)
    convos = [convo_public(db, c["id"]) for c in db.execute("SELECT id FROM convos WHERE session_id=? ORDER BY id", (sid,)).fetchall()]
    words = unit_words(db, s["unit_id"]) if s["unit_id"] else (book_words(db, book["id"]) if book else [])
    return {
        "session": s,
        "unit": unit,
        "book": book,
        "plan_tasks": plan.list_tasks(db, session_id=sid),
        "task": plan.get_task(db, s["task_id"]) if s.get("task_id") else None,
        "unit_words": [{"hanzi": w["hanzi"], "pinyin": w["pinyin"], "meaning": w["primary_meaning"]} for w in words],
        "progress": get_progress(db, s["unit_id"]) if s["unit_id"] else None,
        "review_items": [i for i in items if i["kind"] == "review"],
        "sentence_reviews": srev,
        "quiz_items": [i for i in items if i["kind"] == "quiz"],
        "convos": convos,
        "pass_threshold": PASS_THRESHOLD,
        "stage_labels": STAGE_LABEL,
    }


# ------------------------------------------------------------------ ôn tập & quiz

def answer_quiz_item(db, item_id: int, user_answer: str) -> dict:
    r = db.execute("SELECT * FROM quiz_items WHERE id=?", (item_id,)).fetchone()
    if not r:
        raise LearnError("Không tìm thấy câu hỏi")
    if r["answered_at"]:
        return _item_public(r)
    quiz.answer_item(db, r, user_answer)
    return _item_public(db.execute("SELECT * FROM quiz_items WHERE id=?", (item_id,)).fetchone())


def answer_sentence_review(db, review_id: int, user_answer: str) -> dict:
    r = db.execute(
        "SELECT sr.*, e.original, e.corrected, e.explanation_vi FROM sentence_reviews sr JOIN errors e ON e.id=sr.error_id WHERE sr.id=?",
        (review_id,),
    ).fetchone()
    if not r:
        raise LearnError("Không tìm thấy câu ôn")
    if r["answered_at"]:
        return {"correct": bool(r["correct"]), "feedback": r["feedback"]}
    ua = (user_answer or "").strip()
    res = judge_rewrite(db, r["error_id"], ua)
    db.execute("UPDATE sentence_reviews SET user_answer=?, correct=?, feedback=?, answered_at=? WHERE id=?",
               (ua, 1 if res["correct"] else 0, res["feedback"], now_iso(), review_id))
    return res


def judge_rewrite(db, error_id: int, user_answer: str) -> dict:
    """Chấm câu người học viết lại một câu sai cũ và cập nhật tiến độ sửa lỗi."""
    r = db.execute("SELECT * FROM errors WHERE id=?", (error_id,)).fetchone()
    if not r:
        raise LearnError("Không tìm thấy câu sai")
    ua = (user_answer or "").strip()
    correct, feedback = False, None
    if strip_cjk_punct(ua) == strip_cjk_punct(r["corrected"]):
        correct, feedback = True, "Chính xác!"
    elif ua and llm.is_configured():
        try:
            j = llm.chat_json("judge", prompts.JUDGE_SYSTEM, prompts.judge_user(r["original"], r["corrected"], r["explanation_vi"] or "", ua), 0.1)
            correct, feedback = bool(j.get("correct")), j.get("feedback_vi")
        except llm.LLMError as e:
            feedback = f"Không chấm được bằng AI ({e}). So với câu đúng bên dưới."
    else:
        feedback = "Chưa khớp với câu đúng."
    db.execute(
        "UPDATE errors SET review_count=review_count+1, correct_reviews=correct_reviews+?, "
        "resolved=CASE WHEN correct_reviews+? >= 2 THEN 1 ELSE resolved END WHERE id=?",
        (1 if correct else 0, 1 if correct else 0, error_id),
    )
    return {"correct": correct, "feedback": feedback, "corrected": r["corrected"], "explanation_vi": r["explanation_vi"]}


def start_quiz(db, sid: int) -> None:
    s = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if db.execute("SELECT 1 FROM quiz_items WHERE session_id=? AND kind='quiz' LIMIT 1", (sid,)).fetchone():
        return
    words = unit_words(db, s["unit_id"])
    if len(words) > QUIZ_MAX_QUESTIONS:
        weak = {r["vocab_id"]: r["lapses"] for r in db.execute("SELECT vocab_id, lapses FROM word_mastery").fetchall()}
        random.shuffle(words)
        words.sort(key=lambda w: -weak.get(w["id"], 0))
        words = words[:QUIZ_MAX_QUESTIONS]
    quiz.insert_items(db, sid, "quiz", quiz.assign_types(words, None), vocab_pool(db))


def finish_quiz(db, sid: int) -> dict:
    s = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    rows = db.execute("SELECT correct FROM quiz_items WHERE session_id=? AND kind='quiz'", (sid,)).fetchall()
    if not rows:
        raise LearnError("Chưa có bài kiểm tra")
    score = round(100 * sum(1 for r in rows if r["correct"]) / len(rows))
    db.execute("UPDATE sessions SET quiz_score=? WHERE id=?", (score, sid))
    _bump_progress(db, s["unit_id"], "vocab_best", score)
    return {"score": score, "passed": score >= PASS_THRESHOLD, "progress": get_progress(db, s["unit_id"])}


# ------------------------------------------------------------------ hội thoại

def _targets(db, unit_id: int, stage: str) -> list[dict]:
    words = [w for w in unit_words(db, unit_id) if not w["is_function_word"]]
    weak = {r["vocab_id"]: r["lapses"] for r in db.execute("SELECT vocab_id, lapses FROM word_mastery").fetchall()}
    random.shuffle(words)
    words.sort(key=lambda w: -weak.get(w["id"], 0))
    n = 8 if stage == "controlled" else 10
    return [{"hanzi": w["hanzi"], "meaning": w["primary_meaning"]} for w in words[:n]]


def _book_targets(db, book_id: int, n: int = 12) -> list[str]:
    """Từ mục tiêu cho buổi tổng hợp: ưu tiên từ yếu, rồi từ chưa từng dùng trong hội thoại tổng hợp."""
    words = [w for w in book_words(db, book_id) if not w["is_function_word"]]
    weak = {r["vocab_id"]: r["lapses"] for r in db.execute("SELECT vocab_id, lapses FROM word_mastery").fetchall()}
    used = set()
    for r in db.execute("SELECT used_words FROM convos WHERE book_id=? AND stage='book'", (book_id,)).fetchall():
        used.update(json.loads(r["used_words"] or "[]"))
    random.shuffle(words)
    words.sort(key=lambda w: (-weak.get(w["id"], 0), w["hanzi"] in used))
    return list(dict.fromkeys(w["hanzi"] for w in words))[:n]


def _ai_line(db, convo_id: int, idx: int, hanzi: str, vi: str, oov: list[str], notes: list[dict] | None = None) -> None:
    db.execute(
        "INSERT INTO turns(convo_id, idx, role, hanzi, pinyin, vi, out_of_vocab, notes, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (convo_id, idx, "ai", hanzi, to_display_pinyin(hanzi), vi, json.dumps(oov, ensure_ascii=False),
         json.dumps(notes or [], ensure_ascii=False), now_iso()),
    )


def _new_word_notes(reply: dict, oov: list[str], whitelist: set[str]) -> list[dict]:
    """Chú thích cho mọi từ ngoài vốn từ trong câu AI: lấy giải thích của AI, thiếu thì tự điền pinyin."""
    text = reply.get("hanzi", "")
    notes, seen = [], set()
    for nw in reply.get("new_words") or []:
        # AI đôi khi khai nhầm từ đã học là từ mới -> bỏ
        if (isinstance(nw, dict) and nw.get("hanzi") and nw["hanzi"] in text and nw["hanzi"] not in seen
                and nw["hanzi"] not in whitelist and any(w in nw["hanzi"] or nw["hanzi"] in w for w in oov)):
            seen.add(nw["hanzi"])
            notes.append({"hanzi": nw["hanzi"], "pinyin": nw.get("pinyin") or to_display_pinyin(nw["hanzi"]),
                          "meaning_vi": nw.get("meaning_vi", ""), "explain_vi": nw.get("explain_vi", "")})
    for w in oov:
        if not any(w in n["hanzi"] or n["hanzi"] in w for n in notes):
            notes.append({"hanzi": w, "pinyin": to_display_pinyin(w), "meaning_vi": "", "explain_vi": ""})
    return notes


def _enforce_book(system: str, reply: dict, whitelist: set[str]) -> tuple[dict, list[str], list[dict]]:
    """Hội thoại tổng hợp: cho phép tối đa MAX_NEW_WORDS từ ngoài vốn từ, quá thì yêu cầu AI viết lại."""
    oov = out_of_vocab(reply.get("hanzi", ""), whitelist)
    if len(oov) > prompts.MAX_NEW_WORDS:
        try:
            r2 = llm.chat_json("convo_regen", system, prompts.book_regen_user(reply["hanzi"], oov), 0.4).get("reply") or {}
            if r2.get("hanzi"):
                oov2 = out_of_vocab(r2["hanzi"], whitelist)
                if len(oov2) < len(oov):
                    reply, oov = r2, oov2
        except llm.LLMError:
            pass
    notes = _new_word_notes(reply, oov, whitelist)
    _fill_meanings([(n, reply.get("hanzi", "")) for n in notes])
    return reply, oov, notes


def _fill_meanings(pairs: list[tuple[dict, str]]) -> bool:
    """AI dùng từ mới mà quên giải thích -> hỏi riêng nghĩa (một lần cho cả nhóm). Trả True nếu có thay đổi."""
    missing = [(n, sent) for n, sent in pairs if not n.get("meaning_vi")]
    if not missing or not llm.is_configured():
        return False
    try:
        data = llm.chat_json("explain_words", prompts.EXPLAIN_SYSTEM,
                             prompts.explain_words_user([{"hanzi": n["hanzi"], "sentence": sent} for n, sent in missing]), 0.2)
    except llm.LLMError as e:
        log.warning("explain_words failed: %s", e)
        return False
    got = {w.get("hanzi"): w for w in data.get("words") or [] if isinstance(w, dict)}
    changed = False
    for n, _ in missing:
        w = got.get(n["hanzi"])
        if w and w.get("meaning_vi"):
            n["meaning_vi"] = w["meaning_vi"]
            n["explain_vi"] = n.get("explain_vi") or w.get("explain_vi", "")
            if w.get("pinyin"):
                n["pinyin"] = w["pinyin"]
            changed = True
    return changed


def explain_convo_notes(db, convo_id: int) -> dict:
    """Bổ sung nghĩa cho từ mới còn trống trong các lượt cũ của hội thoại."""
    rows = db.execute("SELECT id, hanzi, notes FROM turns WHERE convo_id=? AND role='ai' AND notes IS NOT NULL", (convo_id,)).fetchall()
    per_turn = [(r["id"], json.loads(r["notes"] or "[]"), r["hanzi"]) for r in rows]
    pairs = [(n, hz) for _, notes, hz in per_turn for n in notes]
    if _fill_meanings(pairs):
        for tid, notes, _ in per_turn:
            db.execute("UPDATE turns SET notes=? WHERE id=?", (json.dumps(notes, ensure_ascii=False), tid))
    return convo_public(db, convo_id)


def _enforce_vocab(system: str, reply: dict, whitelist: set[str], ignore: set[str]) -> tuple[dict, list[str]]:
    oov = out_of_vocab(reply.get("hanzi", ""), whitelist, ignore)
    if oov:
        try:
            r2 = llm.chat_json("convo_regen", system, prompts.convo_regen_user(reply["hanzi"], oov), 0.4).get("reply") or {}
            if r2.get("hanzi"):
                oov2 = out_of_vocab(r2["hanzi"], whitelist, ignore)
                if len(oov2) <= len(oov):
                    reply, oov = r2, oov2
        except llm.LLMError:
            pass
    return reply, oov


def _book_context(db, convo: dict):
    s = row_to_dict(db.execute("SELECT * FROM sessions WHERE id=?", (convo["session_id"],)).fetchone(), ("focus",))
    book = get_book(db, convo["book_id"])
    targets = json.loads(convo["target_words"]) if isinstance(convo["target_words"], str) else convo["target_words"]
    wl = _whitelist(db)
    meaning = {w["hanzi"]: w["primary_meaning"] for w in book_words(db, book["id"])}
    tgt = [{"hanzi": h, "meaning": meaning.get(h, "")} for h in targets]
    system = prompts.book_convo_system(book["title"], s["topic"] or "", sorted(wl), tgt, _grammar_for(db, book["id"]), s["focus"])
    return book, system, wl, targets


def _convo_context(db, convo: dict):
    unit = get_unit(db, convo["unit_id"])
    targets = json.loads(convo["target_words"]) if isinstance(convo["target_words"], str) else convo["target_words"]
    wl = _whitelist(db)
    allowed = sorted(wl) if convo["stage"] == "controlled" else None
    tgt = []
    meaning = {w["hanzi"]: w["primary_meaning"] for w in unit_words(db, unit["id"])}
    for h in targets:
        tgt.append({"hanzi": h, "meaning": meaning.get(h, "")})
    system = prompts.convo_system(convo["stage"], unit, allowed, tgt, _grammar_for(db, unit["book_id"]))
    return unit, system, wl, targets


def start_convo(db, sid: int, stage: str) -> dict:
    s = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not s:
        raise LearnError("Không tìm thấy buổi học")
    if stage == "book" or s["start_stage"] == "book":
        return _start_book_convo(db, s)
    if stage not in ("controlled", "free"):
        raise LearnError("Bước hội thoại không hợp lệ")
    p = get_progress(db, s["unit_id"])
    if not p["unlocked"][stage]:
        raise LearnError(f"Cần đạt ≥ {PASS_THRESHOLD}% ở bước trước để mở '{STAGE_LABEL[stage]}'.")
    existing = db.execute("SELECT id FROM convos WHERE session_id=? AND stage=? AND status='active'", (sid, stage)).fetchone()
    if existing:
        return convo_public(db, existing["id"])
    targets = [t["hanzi"] for t in _targets(db, s["unit_id"], stage)]
    max_turns = CONVO_TURNS_CONTROLLED if stage == "controlled" else CONVO_TURNS_FREE
    cur = db.execute(
        "INSERT INTO convos(session_id, unit_id, stage, max_turns, target_words, used_words, started_at) VALUES(?,?,?,?,?,?,?)",
        (sid, s["unit_id"], stage, max_turns, json.dumps(targets, ensure_ascii=False), "[]", now_iso()),
    )
    cid = cur.lastrowid
    convo = dict(db.execute("SELECT * FROM convos WHERE id=?", (cid,)).fetchone())
    unit, system, wl, _ = _convo_context(db, convo)
    data = llm.chat_json("convo_open", system, prompts.convo_open_user(), 0.7)
    reply = data.get("reply") or {}
    if not reply.get("hanzi"):
        raise llm.LLMError("AI không trả về câu mở đầu")
    oov = []
    if stage == "controlled":
        reply, oov = _enforce_vocab(system, reply, wl, set())
    db.execute("UPDATE convos SET intro_vi=? WHERE id=?", (data.get("intro_vi") or unit.get("scenario_vi"), cid))
    _ai_line(db, cid, 0, reply["hanzi"], reply.get("vi", ""), oov)
    return convo_public(db, cid)


def _start_book_convo(db, s) -> dict:
    existing = db.execute("SELECT id FROM convos WHERE session_id=? AND status!='done'", (s["id"],)).fetchone()
    if existing:
        return convo_public(db, existing["id"])
    if not s["book_id"]:
        raise LearnError("Buổi học này không gắn với quyển nào")
    focus = json.loads(s["focus"] or "{}")
    targets = focus.get("targets") or _book_targets(db, s["book_id"])
    cur = db.execute(
        "INSERT INTO convos(session_id, unit_id, book_id, stage, max_turns, target_words, used_words, started_at) VALUES(?,?,?,?,?,?,?,?)",
        (s["id"], None, s["book_id"], "book", int(focus.get("max_turns") or 8), json.dumps(targets, ensure_ascii=False), "[]", now_iso()),
    )
    cid = cur.lastrowid
    convo = dict(db.execute("SELECT * FROM convos WHERE id=?", (cid,)).fetchone())
    _, system, wl, _ = _book_context(db, convo)
    data = llm.chat_json("convo_open", system, prompts.convo_open_user(new_words=True), 0.7)
    reply = data.get("reply") or {}
    if not reply.get("hanzi"):
        raise llm.LLMError("AI không trả về câu mở đầu")
    reply, oov, notes = _enforce_book(system, reply, wl)
    db.execute("UPDATE convos SET intro_vi=? WHERE id=?", (data.get("intro_vi") or f"Chủ đề: {s['topic']}", cid))
    _ai_line(db, cid, 0, reply["hanzi"], reply.get("vi", ""), oov, notes)
    return convo_public(db, cid)


def convo_message(db, convo_id: int, text: str, input_mode: str | None = None) -> dict:
    convo = row_to_dict(db.execute("SELECT * FROM convos WHERE id=?", (convo_id,)).fetchone())
    if not convo:
        raise LearnError("Không tìm thấy hội thoại")
    if convo["status"] != "active":
        raise LearnError("Hội thoại đã kết thúc")
    text = (text or "").strip()
    if not text:
        raise LearnError("Câu trống")
    if input_mode not in ("hanzi", "pinyin", "voice"):
        input_mode = "pinyin" if is_latin_input(text) else "hanzi"
    turns = rows_to_dicts(db.execute("SELECT * FROM turns WHERE convo_id=? ORDER BY idx", (convo_id,)).fetchall())
    user_turns = sum(1 for t in turns if t["role"] == "user")
    is_book = convo["stage"] == "book"
    if is_book:
        book, system, wl, targets = _book_context(db, convo)
        vocab_rows = book_words(db, book["id"])
    else:
        unit, system, wl, targets = _convo_context(db, convo)
        vocab_rows = unit_words(db, unit["id"])
    used = json.loads(convo["used_words"] or "[]")
    remaining = [t for t in targets if t not in used]
    turns_left = convo["max_turns"] - user_turns
    data = llm.chat_json("convo_turn", system,
                         prompts.convo_turn_user(turns, text, input_mode, remaining, turns_left, new_words=is_book), 0.6)

    ev = data.get("evaluation") or {}
    user_hanzi = text if input_mode == "hanzi" else (data.get("user_hanzi") or text)
    score = int(max(0, min(100, ev.get("score", 0) or 0)))
    ev["score"] = score
    ev["grammar_score"] = int(max(0, min(100, ev.get("grammar_score", score) or 0)))
    # từ mục tiêu dùng đúng
    in_text = set(words_used(user_hanzi, targets))
    llm_used = set(ev.get("used_words") or [])
    good = sorted((in_text & llm_used) | (in_text if ev.get("is_correct") else set()))
    ev["used_words"] = good
    new_used = [w for w in good if w not in used]
    used += new_used
    idx = len(turns)
    cur = db.execute(
        "INSERT INTO turns(convo_id, idx, role, input_mode, raw_text, hanzi, pinyin, eval, score, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (convo_id, idx, "user", input_mode, text, user_hanzi, to_display_pinyin(user_hanzi),
         json.dumps(ev, ensure_ascii=False), score, now_iso()),
    )
    turn_id = cur.lastrowid
    errs = [e for e in (ev.get("errors") or []) if isinstance(e, dict)]
    if (errs or ev.get("is_correct") is False) and ev.get("corrected") and strip_cjk_punct(ev["corrected"]) != strip_cjk_punct(user_hanzi):
        types = ", ".join(sorted({e.get("type") for e in errs if e.get("type")})) or ("khong_dung_tieng_trung" if ev.get("vietnamese_only") else "khac")
        gp = "; ".join(e.get("grammar_point") for e in errs if e.get("grammar_point"))
        # mỗi lỗi một dòng: "phần sai → phần sửa: giải thích"
        expl = "\n".join(
            f"{e.get('original', '')} → {e.get('correction', '')}: {e.get('explanation_vi', '')}".strip() for e in errs
        ) or ev.get("hint_vi", "")
        db.execute(
            "INSERT INTO errors(session_id, turn_id, original, corrected, error_type, grammar_point, explanation_vi, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (convo["session_id"], turn_id, user_hanzi, ev["corrected"], types, gp, expl, now_iso()),
        )
    # cập nhật SRS nhẹ cho từ dùng đúng
    vid = {w["hanzi"]: w["id"] for w in vocab_rows}
    for w in new_used:
        if w in vid:
            srs.update(db, vid[w], 4)
    db.execute("UPDATE convos SET used_words=? WHERE id=?", (json.dumps(used, ensure_ascii=False), convo_id))

    reply = data.get("reply") or {}
    if reply.get("hanzi"):
        oov, notes = [], []
        if convo["stage"] == "controlled":
            reply, oov = _enforce_vocab(system, reply, wl, set())
        elif is_book:
            reply, oov, notes = _enforce_book(system, reply, wl)
        _ai_line(db, convo_id, idx + 1, reply["hanzi"], reply.get("vi", ""), oov, notes)
    if data.get("should_end") or user_turns + 1 >= convo["max_turns"]:
        db.execute("UPDATE convos SET status='ready' WHERE id=?", (convo_id,))
    return convo_public(db, convo_id)


def finish_convo(db, convo_id: int) -> dict:
    convo = row_to_dict(db.execute("SELECT * FROM convos WHERE id=?", (convo_id,)).fetchone(), ("target_words", "used_words"))
    if not convo:
        raise LearnError("Không tìm thấy hội thoại")
    if convo["status"] == "done":
        return {"score": convo["score"], "passed": convo["score"] >= PASS_THRESHOLD,
                "progress": get_progress(db, convo["unit_id"]) if convo["unit_id"] else None}
    scores = [r["score"] for r in db.execute("SELECT score FROM turns WHERE convo_id=? AND role='user'", (convo_id,)).fetchall()]
    if not scores:
        raise LearnError("Bạn chưa nói câu nào")
    avg = sum(scores) / len(scores)
    factor = min(1.0, len(scores) / 4)  # cần ít nhất 4 lượt để được điểm tối đa
    coverage = len(convo["used_words"]) / max(1, len(convo["target_words"]))
    if convo["stage"] in ("free", "book"):
        score = round((0.7 * avg + 0.3 * coverage * 100) * factor)
    else:
        score = round(avg * factor)
    db.execute("UPDATE convos SET status='done', score=?, ended_at=? WHERE id=?", (score, now_iso(), convo_id))
    progress = None
    if convo["stage"] == "book":
        plan.complete_for_session(db, convo["session_id"], score)
    elif convo["unit_id"]:
        _bump_progress(db, convo["unit_id"], f"{convo['stage']}_best", score)
        progress = get_progress(db, convo["unit_id"])
    return {"score": score, "passed": score >= PASS_THRESHOLD, "coverage": round(coverage * 100),
            "turns": len(scores), "progress": progress}


# ------------------------------------------------------------------ báo cáo

def _pct(a, b):
    return round(100 * a / b) if b else None


def compute_skills(db, sid: int) -> dict:
    items = rows_to_dicts(db.execute("SELECT qtype, correct, tone_warning FROM quiz_items WHERE session_id=? AND answered_at IS NOT NULL", (sid,)).fetchall())
    skills: dict[str, int] = {}
    by: dict[str, list] = {}
    for it in items:
        by.setdefault(quiz.QTYPE_SKILL[it["qtype"]], []).append(it)
    for sk, lst in by.items():
        skills[sk] = _pct(sum(1 for x in lst if x["correct"]), len(lst))
    py = [x for x in items if x["qtype"] == "hanzi_pinyin" and x["correct"]]
    if py:
        skills["tones"] = _pct(sum(1 for x in py if not x["tone_warning"]), len(py))
    turns = rows_to_dicts(db.execute(
        "SELECT t.eval, t.score FROM turns t JOIN convos c ON c.id=t.convo_id WHERE c.session_id=? AND t.role='user'", (sid,)
    ).fetchall())
    if turns:
        evs = [json.loads(t["eval"] or "{}") for t in turns]
        skills["communication"] = round(sum(t["score"] for t in turns) / len(turns))
        skills["grammar"] = round(sum(e.get("grammar_score", 0) for e in evs) / len(evs))
    convos = rows_to_dicts(db.execute("SELECT target_words, used_words FROM convos WHERE session_id=?", (sid,)).fetchall())
    tw = sum(len(json.loads(c["target_words"] or "[]")) for c in convos)
    uw = sum(len(json.loads(c["used_words"] or "[]")) for c in convos)
    if convos and tw:
        skills["vocab_usage"] = _pct(uw, tw)
    return {k: v for k, v in skills.items() if v is not None}


def _fallback_report(skills: dict) -> dict:
    ranked = sorted(skills.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "summary_vi": "Báo cáo tự động (chưa dùng được AI để nhận xét chi tiết).",
        "strengths": [f"{SKILL_LABEL[k]}: {v}%" for k, v in ranked if v >= 70][:3],
        "weaknesses": [f"{SKILL_LABEL[k]}: {v}%" for k, v in ranked[::-1] if v < 70][:3],
        "grammar_notes": [],
        "next_steps": ["Ôn lại các từ và câu sai ở đầu buổi học sau."],
    }


def _book_usage(db, sid: int, book_id: int) -> dict:
    """Từ của quyển người học đã tự dùng + từ mới AI đưa vào trong buổi tổng hợp."""
    vocab = [w["hanzi"] for w in book_words(db, book_id)]
    used, new_words = [], {}
    for t in db.execute(
        "SELECT t.role, t.hanzi, t.notes FROM turns t JOIN convos c ON c.id=t.convo_id WHERE c.session_id=? ORDER BY t.id", (sid,)
    ).fetchall():
        if t["role"] == "user":
            used.extend(w for w in words_used(t["hanzi"], vocab) if w not in used)
        else:
            for n in json.loads(t["notes"] or "[]"):
                new_words.setdefault(n["hanzi"], n)
    # bỏ từ con nằm trong từ dài hơn đã dùng (VD 学 trong 学生)
    used = [w for w in used if not any(w != o and w in o for o in used)]
    return {"book_words_used": used, "book_word_total": len(vocab), "new_words": list(new_words.values())}


def finish_session(db, sid: int) -> dict:
    s = row_to_dict(db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone(), ("report",))
    if not s:
        raise LearnError("Không tìm thấy buổi học")
    # đóng các hội thoại còn mở
    for c in db.execute("SELECT id FROM convos WHERE session_id=? AND status!='done'", (sid,)).fetchall():
        try:
            finish_convo(db, c["id"])
        except LearnError:
            db.execute("UPDATE convos SET status='done', score=0 WHERE id=?", (c["id"],))
    if db.execute("SELECT 1 FROM quiz_items WHERE session_id=? AND kind='quiz' LIMIT 1", (sid,)).fetchone() and s["quiz_score"] is None:
        if db.execute("SELECT COUNT(*) c FROM quiz_items WHERE session_id=? AND kind='quiz' AND answered_at IS NULL", (sid,)).fetchone()["c"] == 0:
            finish_quiz(db, sid)
    skills = compute_skills(db, sid)
    unit = get_unit(db, s["unit_id"]) if s["unit_id"] else {}
    is_book = s["start_stage"] == "book"
    if is_book:
        btitle = (db.execute("SELECT title FROM books WHERE id=?", (s["book_id"],)).fetchone() or {"title": ""})["title"]
        unit = {"title_vi": f"Chủ đề: {s['topic']}", "title_zh": "", "book_title": btitle}
    wrong_items = []
    tone_items = []
    for r in db.execute("SELECT * FROM quiz_items WHERE session_id=? AND answered_at IS NOT NULL ORDER BY kind DESC, order_idx", (sid,)).fetchall():
        a = json.loads(r["answer"])
        base = {"hanzi": a["hanzi"], "pinyin": a["pinyin"], "meaning": a["meaning"], "qtype": quiz.QTYPE_LABEL[r["qtype"]],
                "user_answer": r["user_answer"], "kind": r["kind"]}
        if not r["correct"]:
            wrong_items.append(base)
        elif r["tone_warning"]:
            tone_items.append({**base, "note": r["feedback"]})
    convo_errors = rows_to_dicts(db.execute(
        "SELECT original, corrected, error_type, grammar_point, explanation_vi FROM errors WHERE session_id=? ORDER BY id", (sid,)
    ).fetchall())
    good_sentences = list(dict.fromkeys(
        t["hanzi"] for t in db.execute(
            "SELECT t.hanzi, t.score FROM turns t JOIN convos c ON c.id=t.convo_id WHERE c.session_id=? AND t.role='user' AND t.score>=85 ORDER BY t.score DESC LIMIT 5",
            (sid,),
        ).fetchall()
    ))
    stages = []
    if s["quiz_score"] is not None:
        stages.append({"stage": "vocab", "label": STAGE_LABEL["vocab"], "score": s["quiz_score"], "passed": s["quiz_score"] >= PASS_THRESHOLD})
    convo_meta = []
    for c in rows_to_dicts(db.execute("SELECT * FROM convos WHERE session_id=? ORDER BY id", (sid,)).fetchall()):
        tw, uw = json.loads(c["target_words"] or "[]"), json.loads(c["used_words"] or "[]")
        stages.append({"stage": c["stage"], "label": STAGE_LABEL[c["stage"]], "score": c["score"] or 0, "passed": (c["score"] or 0) >= PASS_THRESHOLD})
        convo_meta.append({"stage": c["stage"], "used": uw, "unused": [w for w in tw if w not in uw]})
    rev = rows_to_dicts(db.execute(
        "SELECT sr.correct, e.original, e.corrected FROM sentence_reviews sr JOIN errors e ON e.id=sr.error_id WHERE sr.session_id=? AND sr.answered_at IS NOT NULL",
        (sid,),
    ).fetchall())
    report = {
        "mode": "book" if is_book else "unit",
        "unit": {"title_vi": unit.get("title_vi"), "title_zh": unit.get("title_zh"), "book_title": unit.get("book_title")},
        "stages": stages,
        "skills": skills,
        "skill_labels": SKILL_LABEL,
        "wrong_words": wrong_items,
        "tone_warnings": tone_items,
        "sentence_errors": convo_errors,
        "good_sentences": good_sentences,
        "target_words": convo_meta,
        "sentence_reviews": rev,
        "progress": get_progress(db, s["unit_id"]) if s["unit_id"] else None,
    }
    if is_book:
        report["topic"] = s["topic"]
        report.update(_book_usage(db, sid, s["book_id"]))
    ai = None
    if llm.is_configured() and (wrong_items or convo_errors or skills):
        try:
            keys = ["unit", "stages", "skills", "wrong_words", "tone_warnings", "sentence_errors", "good_sentences", "target_words"]
            if is_book:
                keys += ["topic", "book_words_used", "new_words"]
            payload = {k: report[k] for k in keys}
            ai = llm.chat_json("report", prompts.REPORT_SYSTEM, prompts.report_user(payload), 0.4)
        except llm.LLMError as e:
            log.warning("report llm failed: %s", e)
    report["ai"] = ai or _fallback_report(skills)
    report["ai_generated"] = bool(ai)
    if is_book and not s["task_id"] and not db.execute("SELECT 1 FROM plan_tasks WHERE session_id=?", (sid,)).fetchone():
        # chỉ buổi người học tự mở mới sinh lộ trình (buổi chạy nhiệm vụ thì không, tránh lộ trình lồng nhau)
        plan.build_plan(db, sid, s["book_id"], s["topic"], report)
    db.execute(
        "UPDATE sessions SET status='done', ended_at=?, skill_scores=?, report=? WHERE id=?",
        (now_iso(), json.dumps(skills, ensure_ascii=False), json.dumps(report, ensure_ascii=False), sid),
    )
    return report


# ------------------------------------------------------------------ dashboard

def dashboard(db) -> dict:
    books = rows_to_dicts(db.execute("SELECT * FROM books ORDER BY id").fetchall())
    mastery = {r["vocab_id"]: r for r in db.execute("SELECT * FROM word_mastery").fetchall()}
    now = now_iso()
    totals = {"new": 0, "learning": 0, "weak": 0, "mastered": 0}
    for b in books:
        units = rows_to_dicts(db.execute("SELECT * FROM units WHERE book_id=? ORDER BY idx", (b["id"],)).fetchall())
        for u in units:
            ws = db.execute("SELECT id FROM vocab WHERE unit_id=?", (u["id"],)).fetchall()
            lv = {"new": 0, "learning": 0, "weak": 0, "mastered": 0}
            for w in ws:
                lvl = srs.mastery_level(mastery.get(w["id"]))
                lv[lvl] += 1
                totals[lvl] += 1
            u["word_count"] = len(ws)
            u["mastery"] = lv
            u["progress"] = get_progress(db, u["id"])
        b["units"] = units
        b["word_count"] = db.execute("SELECT COUNT(*) c FROM vocab WHERE book_id=?", (b["id"],)).fetchone()["c"]
    due = db.execute("SELECT COUNT(*) c FROM word_mastery WHERE due_at <= ?", (now,)).fetchone()["c"]
    open_errors = db.execute("SELECT COUNT(*) c FROM errors WHERE resolved=0").fetchone()["c"]
    hist = rows_to_dicts(db.execute(
        "SELECT s.id, s.started_at, s.ended_at, s.skill_scores, s.unit_id, COALESCE(u.title_vi, 'Tổng hợp: ' || s.topic) title_vi "
        "FROM sessions s LEFT JOIN units u ON u.id=s.unit_id "
        "WHERE s.status='done' ORDER BY s.id", ()
    ).fetchall(), ("skill_scores",))
    days = sorted({h["started_at"][:10] for h in hist}, reverse=True)
    streak = 0
    if days:
        d0 = datetime.now(timezone.utc).date()
        dset = set(days)
        from datetime import timedelta
        cur = d0 if d0.isoformat() in dset else d0 - timedelta(days=1)
        while cur.isoformat() in dset:
            streak += 1
            cur -= timedelta(days=1)
    active = row_to_dict(db.execute("SELECT id, unit_id, started_at FROM sessions WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone())
    return {
        "books": books,
        "totals": totals,
        "due_words": due,
        "open_errors": open_errors,
        "history": hist,
        "streak": streak,
        "recommend": recommend(db),
        "active_session": active,
        "open_tasks": db.execute("SELECT COUNT(*) c FROM plan_tasks WHERE status='open'").fetchone()["c"],
        "skill_labels": SKILL_LABEL,
        "stage_labels": STAGE_LABEL,
        "pass_threshold": PASS_THRESHOLD,
        "llm_configured": llm.is_configured(),
    }
