"""Nhập dữ liệu: file từ vựng CSV (định dạng Hanzii) và tài liệu ngữ pháp/bài khoá."""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import threading

from . import llm, prompts
from .db import get_db, now_iso
from .text_utils import CJK_RE, ensure_words

log = logging.getLogger("hanyu.import")

FUNCTION_WORDS = set("了 吧 呢 吗 啊 把 被 都 也 还 再 才 就 给 对 在 从 跟 和 很 太 更 最 又 只 别 着 过 的 得 地 比 向 往 离 为 让 叫".split())
ENRICH_BATCH = 40
UNIT_MIN, UNIT_MAX = 8, 22


# ----------------------------------------------------------------- CSV

def _clean_meanings(raw: str) -> list[str]:
    items = [m.strip() for m in re.split(r"[;；]", raw or "") if m.strip()]
    items = [m for m in items if not m.lower().startswith("đài loan đọc là")]
    return items or [raw.strip()]


def parse_vocab_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:4000]
    delim = ";"
    if sample.count(";") < sample.count("\t"):
        delim = "\t"
    elif sample.count(";") == 0 and sample.count(",") > 0:
        delim = ","
    rows = []
    seen = set()
    for r in csv.reader(io.StringIO(text), delimiter=delim):
        if len(r) < 2:
            continue
        hanzi = r[0].strip()
        if not CJK_RE.search(hanzi):
            continue  # dòng tiêu đề / dòng rỗng
        if hanzi in seen:
            continue
        seen.add(hanzi)
        pinyin = r[1].strip() if len(r) > 1 else ""
        han_viet = r[2].strip() if len(r) > 2 else ""
        meanings = _clean_meanings(r[3]) if len(r) > 3 else []
        note = r[4].strip() if len(r) > 4 else ""
        rows.append({"hanzi": hanzi, "pinyin": pinyin, "han_viet": han_viet, "meanings": meanings, "note": note})
    return rows


def create_book(title: str, filename: str, rows: list[dict]) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO books(title, source_file, status, status_msg, created_at) VALUES(?,?,?,?,?)",
            (title, filename, "importing", "Đang chuẩn hoá từ vựng...", now_iso()),
        )
        book_id = cur.lastrowid
        for w in rows:
            db.execute(
                "INSERT OR IGNORE INTO vocab(book_id, hanzi, pinyin, han_viet, meanings, primary_meaning, is_function_word)"
                " VALUES(?,?,?,?,?,?,?)",
                (book_id, w["hanzi"], w["pinyin"], w["han_viet"], json.dumps(w["meanings"], ensure_ascii=False),
                 w["meanings"][0] if w["meanings"] else "", 1 if w["hanzi"] in FUNCTION_WORDS else 0),
            )
    ensure_words([w["hanzi"] for w in rows])
    return book_id


def _set_status(book_id: int, status: str, msg: str, grouped_by: str | None = None):
    with get_db() as db:
        if grouped_by:
            db.execute("UPDATE books SET status=?, status_msg=?, grouped_by=? WHERE id=?", (status, msg, grouped_by, book_id))
        else:
            db.execute("UPDATE books SET status=?, status_msg=? WHERE id=?", (status, msg, book_id))


def _load_words(book_id: int) -> list[dict]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM vocab WHERE book_id=? ORDER BY id", (book_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["meanings"] = json.loads(d["meanings"])
        out.append(d)
    return out


def enrich_words(book_id: int, only_missing: bool = True) -> int:
    words = [w for w in _load_words(book_id) if not (only_missing and w["enriched"])]
    done = 0
    for i in range(0, len(words), ENRICH_BATCH):
        batch = words[i:i + ENRICH_BATCH]
        _set_status(book_id, "importing", f"AI đang chuẩn hoá nghĩa từ ({i + len(batch)}/{len(words)})...")
        data = llm.chat_json("enrich", prompts.ENRICH_SYSTEM, prompts.enrich_user(batch), temperature=0.2)
        by_h = {x.get("hanzi"): x for x in data.get("words", []) if isinstance(x, dict)}
        with get_db() as db:
            for w in batch:
                x = by_h.get(w["hanzi"])
                if not x:
                    continue
                pm = (x.get("primary_meaning") or "").strip()
                usage = (x.get("usage_vi") or "").strip()
                is_fw = bool(x.get("is_function_word")) or w["hanzi"] in FUNCTION_WORDS
                db.execute(
                    "UPDATE vocab SET primary_meaning=?, is_function_word=?, usage_vi=?, example_zh=?, example_vi=?, enriched=1 WHERE id=?",
                    (pm or w["primary_meaning"], 1 if is_fw else 0, usage, (x.get("example_zh") or "").strip(),
                     (x.get("example_vi") or "").strip(), w["id"]),
                )
                done += 1
    return done


def _fallback_units(words: list[dict]) -> list[dict]:
    units = []
    size = 15
    for i in range(0, len(words), size):
        units.append({
            "title_vi": f"Phần {i // size + 1}", "title_zh": f"第{i // size + 1}部分",
            "scenario_vi": "Trò chuyện với một người bạn Trung Quốc về cuộc sống hằng ngày.",
            "ai_role_vi": "Bạn người Trung Quốc", "user_role_vi": "Bạn",
            "words": [w["hanzi"] for w in words[i:i + size]],
        })
    return units


def _normalize_units(raw_units: list[dict], words: list[dict]) -> list[dict]:
    valid = {w["hanzi"] for w in words}
    used: set[str] = set()
    units = []
    for u in raw_units:
        if not isinstance(u, dict):
            continue
        ws = []
        for h in u.get("words", []) or []:
            h = str(h).strip()
            if h in valid and h not in used:
                ws.append(h)
                used.add(h)
        if not ws:
            continue
        # chia nhỏ bài quá dài
        for k in range(0, len(ws), UNIT_MAX):
            part = dict(u)
            part["words"] = ws[k:k + UNIT_MAX]
            if k:
                part["title_vi"] = f"{u.get('title_vi', 'Bài')} ({k // UNIT_MAX + 1})"
            units.append(part)
    missing = [w for w in words if w["hanzi"] not in used]
    if missing:
        extra = _fallback_units(missing)
        for i, e in enumerate(extra):
            e["title_vi"] = f"Tổng hợp {i + 1}"
            e["title_zh"] = f"综合{i + 1}"
        units.extend(extra)
    # gộp bài quá ngắn vào bài trước
    merged: list[dict] = []
    for u in units:
        if merged and len(u["words"]) < 4 and len(merged[-1]["words"]) + len(u["words"]) <= UNIT_MAX + 4:
            merged[-1]["words"].extend(u["words"])
        else:
            merged.append(u)
    return merged


def group_units(book_id: int) -> str:
    words = _load_words(book_id)
    grouped_by = "fallback"
    units = None
    if llm.is_configured():
        _set_status(book_id, "importing", "AI đang chia bài theo chủ đề...")
        try:
            data = llm.chat_json("group", prompts.GROUP_SYSTEM, prompts.group_user(words), temperature=0.3, timeout=180)
            units = _normalize_units(data.get("units", []), words)
            grouped_by = "llm"
        except llm.LLMError as e:
            log.warning("group failed: %s", e)
    if not units:
        units = _fallback_units(words)
        grouped_by = "fallback"
    with get_db() as db:
        db.execute("UPDATE vocab SET unit_id=NULL WHERE book_id=?", (book_id,))
        db.execute("DELETE FROM units WHERE book_id=?", (book_id,))
        for i, u in enumerate(units):
            cur = db.execute(
                "INSERT INTO units(book_id, idx, title_vi, title_zh, scenario_vi, ai_role_vi, user_role_vi) VALUES(?,?,?,?,?,?,?)",
                (book_id, i + 1, u.get("title_vi") or f"Bài {i + 1}", u.get("title_zh"), u.get("scenario_vi"),
                 u.get("ai_role_vi"), u.get("user_role_vi")),
            )
            uid = cur.lastrowid
            for h in u["words"]:
                db.execute("UPDATE vocab SET unit_id=? WHERE book_id=? AND hanzi=?", (uid, book_id, h))
    return grouped_by


def process_book(book_id: int, regroup_only: bool = False) -> None:
    try:
        notes = []
        if llm.is_configured():
            try:
                enrich_words(book_id, only_missing=True)
            except llm.LLMError as e:
                notes.append(f"Chưa chuẩn hoá được nghĩa: {e}")
        else:
            notes.append("Chưa có API key: dùng nghĩa đầu tiên trong file và chia bài theo thứ tự.")
        grouped_by = group_units(book_id)
        msg = "Sẵn sàng." + (" " + " ".join(notes) if notes else "")
        if grouped_by == "fallback" and llm.is_configured():
            msg += " (AI chia bài thất bại – đang chia theo thứ tự, có thể bấm 'Chia lại bằng AI'.)"
        _set_status(book_id, "ready", msg, grouped_by)
    except Exception as e:  # noqa: BLE001
        log.exception("process_book failed")
        _set_status(book_id, "error", f"Lỗi: {e}")


def start_processing(book_id: int) -> None:
    threading.Thread(target=process_book, args=(book_id,), daemon=True).start()


# ----------------------------------------------------------------- tài liệu

def extract_text(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        import zipfile

        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    return content.decode("utf-8-sig", errors="replace")


def process_material(material_id: int) -> None:
    with get_db() as db:
        m = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not m:
        return
    try:
        data = llm.chat_json("grammar", prompts.GRAMMAR_SYSTEM, prompts.grammar_user(m["text"]), temperature=0.2, timeout=180)
        pts = [p for p in data.get("grammar_points", []) if isinstance(p, dict) and p.get("pattern")]
        with get_db() as db:
            db.execute("DELETE FROM grammar_points WHERE material_id=?", (material_id,))
            for p in pts[:40]:
                db.execute(
                    "INSERT INTO grammar_points(book_id, material_id, pattern, explanation_vi, example_zh, example_vi) VALUES(?,?,?,?,?,?)",
                    (m["book_id"], material_id, p["pattern"], p.get("explanation_vi"), p.get("example_zh"), p.get("example_vi")),
                )
            db.execute("UPDATE materials SET status='ready', status_msg=? WHERE id=?", (f"Đã rút ra {len(pts[:40])} điểm ngữ pháp", material_id))
    except Exception as e:  # noqa: BLE001
        with get_db() as db:
            db.execute("UPDATE materials SET status='error', status_msg=? WHERE id=?", (str(e), material_id))


def start_material(material_id: int) -> None:
    threading.Thread(target=process_material, args=(material_id,), daemon=True).start()
