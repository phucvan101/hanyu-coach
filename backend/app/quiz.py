"""Sinh câu hỏi kiểm tra từ vựng và chấm điểm."""
from __future__ import annotations

import json
import random

from . import srs
from .db import now_iso
from .pinyin_utils import check_pinyin, normalize_letters
from .text_utils import CJK_RE, strip_cjk_punct

QTYPE_LABEL = {
    "hanzi_meaning": "Hán tự → nghĩa",
    "meaning_hanzi": "Nghĩa → Hán tự",
    "hanzi_pinyin": "Hán tự → pinyin",
    "listen_hanzi": "Nghe → chọn từ",
    "meaning_write": "Nghĩa → tự gõ Hán tự",
    "cloze": "Điền từ vào câu",
}
# kỹ năng mà mỗi dạng câu đo
QTYPE_SKILL = {
    "hanzi_meaning": "recognition",
    "meaning_hanzi": "recognition",
    "cloze": "recognition",
    "hanzi_pinyin": "pinyin",
    "listen_hanzi": "listening",
    "meaning_write": "writing",
}


def _has_cloze(w) -> bool:
    return bool(w["example_zh"]) and w["hanzi"] in (w["example_zh"] or "")


def allowed_types(w) -> list[str]:
    if w["is_function_word"]:
        t = ["hanzi_pinyin", "listen_hanzi"]
        if _has_cloze(w):
            t = ["cloze", "cloze", "hanzi_pinyin", "listen_hanzi"]
        return t
    t = ["hanzi_meaning", "meaning_hanzi", "hanzi_pinyin", "listen_hanzi", "meaning_write"]
    if _has_cloze(w):
        t.append("cloze")
    return t


def _pick_distinct(cands, n, key):
    out, seen = [], set()
    for c in cands:
        k = key(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
        if len(out) >= n:
            break
    return out


def _distractors(w, pool, qtype, n=3):
    others = [p for p in pool if p["hanzi"] != w["hanzi"]]
    random.shuffle(others)
    same_unit = [p for p in others if p["unit_id"] == w["unit_id"]]
    rest = [p for p in others if p["unit_id"] != w["unit_id"]]
    if qtype in ("hanzi_meaning",):
        cands = [p for p in same_unit + rest if not p["is_function_word"] and p["primary_meaning"] != w["primary_meaning"]]
        return _pick_distinct(cands, n, lambda p: p["primary_meaning"])
    if qtype == "listen_hanzi":
        letters = normalize_letters(w["pinyin"])
        first = letters[:2]
        similar = [p for p in others if normalize_letters(p["pinyin"]) == letters]
        near = [p for p in others if normalize_letters(p["pinyin"])[:2] == first and p not in similar]
        same_len = [p for p in others if len(p["hanzi"]) == len(w["hanzi"])]
        return _pick_distinct(similar + near + same_len + others, n, lambda p: p["hanzi"])
    if qtype == "cloze":
        if w["is_function_word"]:
            cands = [p for p in others if p["is_function_word"]] + others
        else:
            cands = [p for p in same_unit + rest if len(p["hanzi"]) == len(w["hanzi"]) and not p["is_function_word"]] + others
        return _pick_distinct(cands, n, lambda p: p["hanzi"])
    # meaning_hanzi
    cands = [p for p in same_unit if len(p["hanzi"]) == len(w["hanzi"])] + same_unit + [p for p in rest if len(p["hanzi"]) == len(w["hanzi"])] + rest
    cands = [p for p in cands if p["primary_meaning"] != w["primary_meaning"]]
    return _pick_distinct(cands, n, lambda p: p["hanzi"])


def make_item(w, qtype, pool) -> tuple[dict, dict]:
    reveal = {
        "hanzi": w["hanzi"], "pinyin": w["pinyin"], "meaning": w["primary_meaning"], "han_viet": w["han_viet"],
        "usage": w["usage_vi"], "example_zh": w["example_zh"], "example_vi": w["example_vi"],
    }
    if qtype == "hanzi_meaning":
        opts = [w["primary_meaning"]] + [d["primary_meaning"] for d in _distractors(w, pool, qtype)]
        random.shuffle(opts)
        return {"hanzi": w["hanzi"], "options": opts}, {"value": w["primary_meaning"], **reveal}
    if qtype == "meaning_hanzi":
        opts = [w["hanzi"]] + [d["hanzi"] for d in _distractors(w, pool, qtype)]
        random.shuffle(opts)
        return {"meaning": w["primary_meaning"], "options": opts}, {"value": w["hanzi"], **reveal}
    if qtype == "listen_hanzi":
        opts = [w["hanzi"]] + [d["hanzi"] for d in _distractors(w, pool, qtype)]
        random.shuffle(opts)
        return {"audio_text": w["hanzi"], "options": opts}, {"value": w["hanzi"], **reveal}
    if qtype == "hanzi_pinyin":
        return {"hanzi": w["hanzi"], "meaning": w["primary_meaning"]}, {"value": w["pinyin"], **reveal}
    if qtype == "meaning_write":
        return {"meaning": w["primary_meaning"], "han_viet": w["han_viet"], "length": len(w["hanzi"])}, {"value": w["hanzi"], **reveal}
    if qtype == "cloze":
        sent = w["example_zh"].replace(w["hanzi"], "＿＿", 1)
        opts = [w["hanzi"]] + [d["hanzi"] for d in _distractors(w, pool, qtype)]
        random.shuffle(opts)
        return {"sentence": sent, "sentence_vi": w["example_vi"], "options": opts}, {"value": w["hanzi"], **reveal}
    raise ValueError(qtype)


def assign_types(words, pool, recent_wrong_types=None) -> list[tuple[dict, str]]:
    counts: dict[str, int] = {}
    out = []
    order = list(words)
    random.shuffle(order)
    for w in order:
        types = allowed_types(w)
        random.shuffle(types)
        qt = min(types, key=lambda t: counts.get(t, 0))
        counts[qt] = counts.get(qt, 0) + 1
        out.append((w, qt))
    return out


def insert_items(db, session_id: int, kind: str, pairs, pool, start_idx: int = 0) -> None:
    for i, (w, qt) in enumerate(pairs):
        payload, answer = make_item(w, qt, pool)
        payload["qtype"] = qt
        payload["label"] = QTYPE_LABEL[qt]
        db.execute(
            "INSERT INTO quiz_items(session_id, kind, order_idx, vocab_id, qtype, payload, answer) VALUES(?,?,?,?,?,?,?)",
            (session_id, kind, start_idx + i, w["id"], qt, json.dumps(payload, ensure_ascii=False), json.dumps(answer, ensure_ascii=False)),
        )


def grade(qtype: str, answer: dict, hanzi: str, user_answer: str) -> dict:
    ua = (user_answer or "").strip()
    res = {"correct": False, "tone_warning": None, "feedback": None}
    if qtype in ("hanzi_meaning", "meaning_hanzi", "listen_hanzi", "cloze"):
        res["correct"] = ua == answer["value"]
    elif qtype == "hanzi_pinyin":
        c = check_pinyin(ua, hanzi, answer["value"])
        res["correct"] = c["correct"]
        if c["correct"] and c["tone_status"] != "ok":
            res["tone_warning"] = c["tone_status"]
            res["feedback"] = c["warning"]
        elif c["correct"] and c["warning"]:
            res["feedback"] = c["warning"]
    elif qtype == "meaning_write":
        clean = strip_cjk_punct(ua)
        if clean == hanzi:
            res["correct"] = True
        elif clean and not CJK_RE.search(clean):
            c = check_pinyin(clean, hanzi, answer["pinyin"])
            res["feedback"] = ("Bạn gõ đúng pinyin nhưng phần này cần chọn chữ Hán (dùng bộ gõ)." if c["correct"]
                               else "Phần này cần nhập chữ Hán.")
    return res


def answer_item(db, item_row, user_answer: str) -> dict:
    answer = json.loads(item_row["answer"])
    g = grade(item_row["qtype"], answer, answer["hanzi"], user_answer)
    db.execute(
        "UPDATE quiz_items SET user_answer=?, correct=?, tone_warning=?, feedback=?, answered_at=? WHERE id=?",
        (user_answer, 1 if g["correct"] else 0, g["tone_warning"], g["feedback"], now_iso(), item_row["id"]),
    )
    if item_row["vocab_id"]:
        tone_err = item_row["qtype"] == "hanzi_pinyin" and g["tone_warning"] == "mismatch"
        srs.update(db, item_row["vocab_id"], srs.quality_from(g["correct"], bool(g["tone_warning"])), tone_error=tone_err)
    return {**g, "answer": answer}
