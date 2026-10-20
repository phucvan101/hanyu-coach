"""Lộ trình cải thiện: các nhiệm vụ bấm làm ngay, sinh từ báo cáo buổi hội thoại tổng hợp."""
from __future__ import annotations

import json

from .db import now_iso, row_to_dict, rows_to_dicts

KIND_LABEL = {
    "rewrite": "Viết lại câu sai",
    "grammar_convo": "Hội thoại luyện ngữ pháp",
    "pinyin_drill": "Ôn pinyin",
    "words_convo": "Hội thoại dùng từ",
}
MINI_TURNS = 6


def _public(db, r, detail: bool = False) -> dict:
    t = row_to_dict(r, ("payload",))
    t["kind_label"] = KIND_LABEL.get(t["kind"], t["kind"])
    src = db.execute("SELECT topic, started_at FROM sessions WHERE id=?", (t["session_id"],)).fetchone()
    t["source_topic"] = src["topic"] if src else None
    if detail:
        p = t["payload"]
        if t["kind"] == "pinyin_drill":
            ids = p.get("vocab_ids") or []
            rows = {r["id"]: r for r in db.execute(
                f"SELECT id, hanzi, primary_meaning, han_viet FROM vocab WHERE id IN ({','.join('?' * len(ids))})", ids
            ).fetchall()} if ids else {}
            t["items"] = [{"vocab_id": i, "hanzi": rows[i]["hanzi"], "meaning": rows[i]["primary_meaning"],
                           "han_viet": rows[i]["han_viet"]} for i in ids if i in rows]
        elif t["kind"] == "rewrite":
            ids = p.get("error_ids") or []
            t["items"] = rows_to_dicts(db.execute(
                f"SELECT id, original, grammar_point, resolved FROM errors WHERE id IN ({','.join('?' * len(ids))}) ORDER BY id", ids
            ).fetchall()) if ids else []
    return t


def list_tasks(db, session_id: int | None = None, status: str | None = None) -> list[dict]:
    q, args = "SELECT * FROM plan_tasks WHERE 1=1", []
    if session_id is not None:
        q += " AND session_id=?"
        args.append(session_id)
    if status:
        q += " AND status=?"
        args.append(status)
    return [_public(db, r) for r in db.execute(q + " ORDER BY session_id DESC, idx", args).fetchall()]


def get_task(db, task_id: int, detail: bool = False) -> dict | None:
    r = db.execute("SELECT * FROM plan_tasks WHERE id=?", (task_id,)).fetchone()
    return _public(db, r, detail) if r else None


def _add(db, sid: int, idx: int, kind: str, title: str, detail: str, payload: dict) -> None:
    db.execute(
        "INSERT INTO plan_tasks(session_id, idx, kind, title_vi, detail_vi, payload, created_at) VALUES(?,?,?,?,?,?,?)",
        (sid, idx, kind, title, detail, json.dumps(payload, ensure_ascii=False), now_iso()),
    )


def build_plan(db, sid: int, book_id: int, topic: str, report: dict) -> None:
    tasks = []
    errs = db.execute("SELECT id, grammar_point FROM errors WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    if errs:
        tasks.append(("rewrite", f"Viết lại {len(errs)} câu bạn nói sai",
                      "Viết lại từng câu cho đúng; AI chấm và giải thích. Đúng 2 lần thì câu được tính là đã sửa xong.",
                      {"error_ids": [e["id"] for e in errs]}))

    # ngữ pháp sai: ưu tiên điểm xuất hiện nhiều lần, kèm giải thích từ báo cáo AI
    count: dict[str, int] = {}
    for e in errs:
        for gp in (e["grammar_point"] or "").split(";"):
            gp = gp.strip()
            if gp:
                count[gp] = count.get(gp, 0) + 1
    notes = {g.get("point", ""): g.get("explanation_vi", "") for g in (report.get("ai") or {}).get("grammar_notes") or []
             if isinstance(g, dict)}
    for p in notes:
        if p and p not in count:
            count[p] = 0
    for gp in sorted(count, key=lambda k: -count[k])[:2]:
        tasks.append(("grammar_convo", f"Hội thoại ngắn luyện: {gp}",
                      notes.get(gp) or "AI dẫn dắt để bạn phải dùng đúng điểm ngữ pháp này nhiều lần.",
                      {"topic": topic, "grammar": [gp], "max_turns": MINI_TURNS}))

    # từ cần ôn: từ mục tiêu chưa dùng + từ yếu của quyển
    unused = list(dict.fromkeys(w for t in report.get("target_words") or [] for w in t.get("unused", [])))
    vocab = {r["hanzi"]: r["id"] for r in db.execute(
        "SELECT id, hanzi FROM vocab WHERE book_id=? AND unit_id IS NOT NULL", (book_id,)).fetchall()}
    weak = [r["hanzi"] for r in db.execute(
        """SELECT v.hanzi FROM word_mastery m JOIN vocab v ON v.id=m.vocab_id
           WHERE v.book_id=? AND m.lapses>0 AND m.reps=0 ORDER BY m.lapses DESC LIMIT 15""", (book_id,)).fetchall()]
    drill = [vocab[h] for h in dict.fromkeys(unused + weak) if h in vocab][:15]
    if drill:
        tasks.append(("pinyin_drill", f"Ôn pinyin {len(drill)} từ chưa dùng / còn yếu",
                      "Nhìn chữ Hán, gõ pinyin có thanh điệu.", {"vocab_ids": drill}))
    if len(unused) >= 3:
        tw = unused[:8]
        tasks.append(("words_convo", f"Hội thoại dùng lại {len(tw)} từ bạn chưa dùng",
                      "Cùng chủ đề, nhưng bạn phải tự đưa các từ này vào câu: " + "、".join(tw),
                      {"topic": topic, "targets": tw, "max_turns": MINI_TURNS,
                       "note_vi": "Người học cần tự dùng các từ mục tiêu; hãy đặt câu hỏi gợi đúng các từ đó."}))
    for i, (kind, title, detail, payload) in enumerate(tasks):
        _add(db, sid, i, kind, title, detail, payload)


def start_task(db, task_id: int) -> dict:
    """Nhiệm vụ hội thoại: tạo buổi tổng hợp mini. Nhiệm vụ khác: FE tự mở trang tương ứng."""
    from . import learning  # tránh import vòng

    t = get_task(db, task_id)
    if not t:
        raise learning.LearnError("Không tìm thấy nhiệm vụ")
    if t["kind"] not in ("grammar_convo", "words_convo"):
        return {"task": t}
    if t["run_session_id"]:
        run = db.execute("SELECT status FROM sessions WHERE id=?", (t["run_session_id"],)).fetchone()
        if run and run["status"] == "active":
            return {"task": t, "session_id": t["run_session_id"]}
    src = db.execute("SELECT book_id FROM sessions WHERE id=?", (t["session_id"],)).fetchone()
    p = t["payload"]
    focus = {k: p[k] for k in ("grammar", "targets", "note_vi") if p.get(k)}
    sid = learning.create_book_session(db, src["book_id"], p.get("topic") or t["source_topic"] or "Chủ đề tự do",
                                       int(p.get("max_turns") or MINI_TURNS), focus, task_id=task_id)
    db.execute("UPDATE plan_tasks SET run_session_id=? WHERE id=?", (sid, task_id))
    return {"task": t, "session_id": sid}


def complete_task(db, task_id: int, score: int | None) -> dict | None:
    db.execute("UPDATE plan_tasks SET status='done', score=?, done_at=? WHERE id=?",
               (None if score is None else int(max(0, min(100, score))), now_iso(), task_id))
    return get_task(db, task_id)


def complete_for_session(db, session_id: int, score: int) -> None:
    db.execute("UPDATE plan_tasks SET status='done', score=?, done_at=? WHERE run_session_id=?",
               (score, now_iso(), session_id))
