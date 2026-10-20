from __future__ import annotations

import hashlib
import logging
import random
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import drill, ime, importer, learning, llm, plan, srs
from .config import STATIC_DIR, TTS_CACHE_DIR
from .db import get_db, get_setting, init_db, now_iso, row_to_dict, rows_to_dicts, set_setting
from .text_utils import ensure_words

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")



def _startup():
    init_db()
    with get_db() as db:
        ensure_words([r["hanzi"] for r in db.execute("SELECT hanzi FROM vocab").fetchall()])
        # sách đang import dở khi tắt app -> chạy lại
        for b in db.execute("SELECT id FROM books WHERE status='importing'").fetchall():
            importer.start_processing(b["id"])
        for m in db.execute("SELECT id FROM materials WHERE status='processing'").fetchall():
            importer.start_material(m["id"])


@asynccontextmanager
async def lifespan(_app):
    _startup()
    yield


app = FastAPI(title="Hanyu Coach", version="1.0.0", lifespan=lifespan)


@app.exception_handler(learning.LearnError)
async def _learn_err(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(llm.LLMError)
async def _llm_err(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=502)


# ------------------------------------------------------------------ dashboard

@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard():
    with get_db() as db:
        return learning.dashboard(db)


# ------------------------------------------------------------------ thư viện

@app.get("/api/books")
def list_books():
    with get_db() as db:
        books = rows_to_dicts(db.execute("SELECT * FROM books ORDER BY id").fetchall())
        for b in books:
            b["word_count"] = db.execute("SELECT COUNT(*) c FROM vocab WHERE book_id=?", (b["id"],)).fetchone()["c"]
            b["unit_count"] = db.execute("SELECT COUNT(*) c FROM units WHERE book_id=?", (b["id"],)).fetchone()["c"]
            b["materials"] = rows_to_dicts(db.execute(
                "SELECT id, filename, status, status_msg, created_at FROM materials WHERE book_id=? ORDER BY id", (b["id"],)
            ).fetchall())
            b["grammar_count"] = db.execute("SELECT COUNT(*) c FROM grammar_points WHERE book_id=?", (b["id"],)).fetchone()["c"]
        return books


@app.post("/api/books/import")
async def import_book(file: UploadFile = File(...), title: str = Form("")):
    content = await file.read()
    rows = importer.parse_vocab_csv(content)
    if not rows:
        raise HTTPException(400, "Không đọc được từ nào. File cần dạng: Hán tự;pinyin;Hán Việt;nghĩa")
    name = title.strip() or Path(file.filename or "Quyển mới").stem
    book_id = importer.create_book(name, file.filename or "", rows)
    importer.start_processing(book_id)
    return {"id": book_id, "word_count": len(rows)}


@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    with get_db() as db:
        b = row_to_dict(db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone())
        if not b:
            raise HTTPException(404, "Không tìm thấy")
        mastery = {r["vocab_id"]: r for r in db.execute("SELECT * FROM word_mastery").fetchall()}
        units = rows_to_dicts(db.execute("SELECT * FROM units WHERE book_id=? ORDER BY idx", (book_id,)).fetchall())
        for u in units:
            ws = rows_to_dicts(db.execute("SELECT * FROM vocab WHERE unit_id=? ORDER BY id", (u["id"],)).fetchall(), ("meanings",))
            for w in ws:
                w["level"] = srs.mastery_level(mastery.get(w["id"]))
            u["words"] = ws
            u["progress"] = learning.get_progress(db, u["id"])
        b["units"] = units
        b["unassigned"] = rows_to_dicts(db.execute("SELECT * FROM vocab WHERE book_id=? AND unit_id IS NULL", (book_id,)).fetchall(), ("meanings",))
        b["materials"] = rows_to_dicts(db.execute("SELECT id, filename, status, status_msg, created_at FROM materials WHERE book_id=?", (book_id,)).fetchall())
        b["grammar_points"] = rows_to_dicts(db.execute("SELECT * FROM grammar_points WHERE book_id=? ORDER BY id", (book_id,)).fetchall())
        return b


@app.patch("/api/books/{book_id}")
def rename_book(book_id: int, body: dict = Body(...)):
    with get_db() as db:
        if body.get("title"):
            db.execute("UPDATE books SET title=? WHERE id=?", (body["title"].strip(), book_id))
    return {"ok": True}


@app.post("/api/books/{book_id}/regroup")
def regroup(book_id: int):
    with get_db() as db:
        db.execute("UPDATE books SET status='importing', status_msg='Đang chia lại bài...' WHERE id=?", (book_id,))
    importer.start_processing(book_id)
    return {"ok": True}


@app.delete("/api/books/{book_id}")
def delete_book(book_id: int):
    with get_db() as db:
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
    return {"ok": True}


@app.patch("/api/units/{unit_id}")
def update_unit(unit_id: int, body: dict = Body(...)):
    fields = {k: body[k] for k in ("title_vi", "title_zh", "scenario_vi", "ai_role_vi", "user_role_vi") if k in body}
    with get_db() as db:
        for k, v in fields.items():
            db.execute(f"UPDATE units SET {k}=? WHERE id=?", (v, unit_id))
    return {"ok": True}


@app.patch("/api/vocab/{vocab_id}")
def update_vocab(vocab_id: int, body: dict = Body(...)):
    with get_db() as db:
        if "primary_meaning" in body:
            db.execute("UPDATE vocab SET primary_meaning=? WHERE id=?", (body["primary_meaning"].strip(), vocab_id))
        if "unit_id" in body:
            db.execute("UPDATE vocab SET unit_id=? WHERE id=?", (body["unit_id"], vocab_id))
        if "is_function_word" in body:
            db.execute("UPDATE vocab SET is_function_word=? WHERE id=?", (1 if body["is_function_word"] else 0, vocab_id))
        if "pinyin" in body:
            db.execute("UPDATE vocab SET pinyin=? WHERE id=?", (body["pinyin"].strip(), vocab_id))
    return {"ok": True}


@app.post("/api/books/{book_id}/materials")
async def upload_material(book_id: int, file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = importer.extract_text(file.filename or "", content)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Không đọc được file: {e}")
    if len(text.strip()) < 20:
        raise HTTPException(400, "File gần như không có chữ (PDF scan ảnh chưa được hỗ trợ).")
    if not llm.is_configured():
        raise HTTPException(400, "Cần nhập API key trong Cài đặt để AI đọc tài liệu ngữ pháp.")
    with get_db() as db:
        cur = db.execute("INSERT INTO materials(book_id, filename, text, created_at) VALUES(?,?,?,?)",
                         (book_id, file.filename or "tai-lieu", text, now_iso()))
        mid = cur.lastrowid
    importer.start_material(mid)
    return {"id": mid}


@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    with get_db() as db:
        db.execute("DELETE FROM materials WHERE id=?", (material_id,))
    return {"ok": True}


# ------------------------------------------------------------------ học

@app.post("/api/sessions")
def create_session(body: dict = Body(default={})):
    with get_db() as db:
        sid = learning.create_session(db, body.get("unit_id"), body.get("stage"))
        return learning.session_state(db, sid)


@app.get("/api/sessions")
def list_sessions(limit: int = 50):
    with get_db() as db:
        rows = rows_to_dicts(db.execute(
            "SELECT s.id, s.unit_id, s.start_stage, s.status, s.started_at, s.ended_at, s.quiz_score, s.skill_scores, s.topic, s.task_id, "
            "COALESCE(u.title_vi, 'Tổng hợp: ' || s.topic) title_vi "
            "FROM sessions s LEFT JOIN units u ON u.id=s.unit_id ORDER BY s.id DESC LIMIT ?", (limit,)
        ).fetchall(), ("skill_scores",))
        return rows


@app.get("/api/sessions/{sid}")
def get_session(sid: int):
    with get_db() as db:
        return learning.session_state(db, sid)


@app.post("/api/book-sessions")
def create_book_session(body: dict = Body(...)):
    """Hội thoại tổng hợp cả quyển với chủ đề tự chọn."""
    try:
        book_id, turns = int(body.get("book_id") or 0), int(body.get("max_turns") or 8)
    except (TypeError, ValueError):
        raise HTTPException(400, "Dữ liệu không hợp lệ")
    with get_db() as db:
        sid = learning.create_book_session(db, book_id, str(body.get("topic", "")), turns)
        return learning.session_state(db, sid)


@app.get("/api/plan-tasks")
def list_plan_tasks(status: str | None = None, session_id: int | None = None):
    with get_db() as db:
        return plan.list_tasks(db, session_id=session_id, status=status)


@app.get("/api/plan-tasks/{task_id}")
def get_plan_task(task_id: int):
    with get_db() as db:
        t = plan.get_task(db, task_id, detail=True)
        if not t:
            raise HTTPException(404, "Không tìm thấy nhiệm vụ")
        return t


@app.post("/api/plan-tasks/{task_id}/start")
def start_plan_task(task_id: int):
    with get_db() as db:
        return plan.start_task(db, task_id)


@app.post("/api/plan-tasks/{task_id}/complete")
def complete_plan_task(task_id: int, body: dict = Body(default={})):
    with get_db() as db:
        if not plan.get_task(db, task_id):
            raise HTTPException(404, "Không tìm thấy nhiệm vụ")
        return plan.complete_task(db, task_id, body.get("score"))


@app.post("/api/errors/{error_id}/rewrite")
def rewrite_error(error_id: int, body: dict = Body(...)):
    with get_db() as db:
        return learning.judge_rewrite(db, error_id, str(body.get("answer", "")))


@app.post("/api/quiz-items/{item_id}/answer")
def answer_item(item_id: int, body: dict = Body(...)):
    with get_db() as db:
        return learning.answer_quiz_item(db, item_id, str(body.get("answer", "")))


@app.post("/api/sentence-reviews/{rid}/answer")
def answer_sentence(rid: int, body: dict = Body(...)):
    with get_db() as db:
        return learning.answer_sentence_review(db, rid, str(body.get("answer", "")))


@app.post("/api/sessions/{sid}/quiz/start")
def start_quiz(sid: int):
    with get_db() as db:
        learning.start_quiz(db, sid)
        return learning.session_state(db, sid)


@app.post("/api/sessions/{sid}/quiz/finish")
def finish_quiz(sid: int):
    with get_db() as db:
        return learning.finish_quiz(db, sid)


@app.post("/api/sessions/{sid}/convo")
def start_convo(sid: int, body: dict = Body(...)):
    with get_db() as db:
        return learning.start_convo(db, sid, body.get("stage", "controlled"))


@app.post("/api/convos/{cid}/message")
def convo_message(cid: int, body: dict = Body(...)):
    with get_db() as db:
        return learning.convo_message(db, cid, body.get("text", ""), body.get("input_mode"))


@app.post("/api/convos/{cid}/explain-notes")
def explain_notes(cid: int):
    with get_db() as db:
        return learning.explain_convo_notes(db, cid)


@app.post("/api/convos/{cid}/finish")
def finish_convo(cid: int):
    with get_db() as db:
        return learning.finish_convo(db, cid)


@app.post("/api/sessions/{sid}/finish")
def finish_session(sid: int):
    with get_db() as db:
        return learning.finish_session(db, sid)


@app.delete("/api/sessions/{sid}")
def delete_session(sid: int):
    with get_db() as db:
        db.execute("DELETE FROM sessions WHERE id=?", (sid,))
    return {"ok": True}


# ------------------------------------------------------------------ luyện Hán tự → pinyin

@app.get("/api/drill/pinyin/options")
def drill_options():
    with get_db() as db:
        return drill.options(db)


@app.post("/api/drill/pinyin/deck")
def drill_deck(body: dict = Body(default={})):
    with get_db() as db:
        return drill.deck(db, str(body.get("scope", "all")), body.get("id"), int(body.get("limit") or 0))


@app.post("/api/drill/pinyin/{vocab_id}/check")
def drill_check(vocab_id: int, body: dict = Body(...)):
    with get_db() as db:
        try:
            return drill.check(db, vocab_id, str(body.get("answer", "")), bool(body.get("record", True)))
        except LookupError as e:
            raise HTTPException(404, str(e))


# ------------------------------------------------------------------ game bắn chữ Hán

@app.post("/api/game/deck")
def game_deck(body: dict = Body(default={})):
    with get_db() as db:
        return drill.game_deck(db, str(body.get("scope", "all")), body.get("id"))


@app.post("/api/game/bosses")
def game_bosses(body: dict = Body(default={})):
    with get_db() as db:
        return drill.game_bosses(db, str(body.get("scope", "all")), body.get("id"))


@app.post("/api/game/results")
def game_results(body: dict = Body(default={})):
    with get_db() as db:
        return drill.game_results(db, list(body.get("results") or []))


# ------------------------------------------------------------------ flashcard (dùng chung phạm vi với luyện pinyin)

@app.post("/api/flashcards/deck")
def flashcard_deck(body: dict = Body(default={})):
    with get_db() as db:
        return drill.deck(db, str(body.get("scope", "all")), body.get("id"), int(body.get("limit") or 0), full=True)


@app.post("/api/flashcards/{vocab_id}/rate")
def flashcard_rate(vocab_id: int, body: dict = Body(...)):
    with get_db() as db:
        try:
            return drill.rate(db, vocab_id, int(body.get("rating") or 0))
        except ValueError as e:
            raise HTTPException(400, str(e))
        except LookupError as e:
            raise HTTPException(404, str(e))


# ------------------------------------------------------------------ sổ tay

@app.get("/api/errors")
def list_errors(resolved: int | None = None):
    with get_db() as db:
        q = "SELECT e.*, s.unit_id, u.title_vi FROM errors e LEFT JOIN sessions s ON s.id=e.session_id LEFT JOIN units u ON u.id=s.unit_id"
        args = ()
        if resolved is not None:
            q += " WHERE e.resolved=?"
            args = (resolved,)
        return rows_to_dicts(db.execute(q + " ORDER BY e.id DESC LIMIT 300", args).fetchall())


@app.get("/api/words")
def list_words():
    with get_db() as db:
        rows = rows_to_dicts(db.execute(
            """SELECT v.id, v.hanzi, v.pinyin, v.primary_meaning, v.han_viet, v.unit_id, u.title_vi,
                      m.correct, m.wrong, m.tone_errors, m.lapses, m.interval_days, m.due_at, m.last_seen, m.reps
               FROM vocab v LEFT JOIN units u ON u.id=v.unit_id LEFT JOIN word_mastery m ON m.vocab_id=v.id
               ORDER BY COALESCE(m.wrong,0) DESC, v.id"""
        ).fetchall())
        for r in rows:
            r["level"] = srs.mastery_level(r if r["last_seen"] else None)
        return rows


# ------------------------------------------------------------------ bộ gõ, giọng nói

@app.get("/api/ime")
def ime_candidates(q: str = Query("")):
    with get_db() as db:
        vocab = [r["hanzi"] for r in db.execute("SELECT DISTINCT hanzi FROM vocab").fetchall()]
    return ime.candidates(q, vocab)


@app.post("/api/stt")
async def stt(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) < 2000:
        raise HTTPException(400, "Đoạn ghi âm quá ngắn")
    return {"text": llm.transcribe(data)}


TTS_MIX_VOICES = [
    "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural",
    "zh-CN-YunyangNeural", "zh-CN-YunxiaNeural", "zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural", "zh-TW-YunJheNeural",
]


@app.get("/api/tts")
async def tts(text: str = Query(..., max_length=500), rate: int = Query(-10, ge=-70, le=50), voice: str = Query("")):
    with get_db() as db:
        voice = voice or get_setting(db, "tts_voice", "zh-CN-XiaoxiaoNeural")
    if voice == "mix":
        voice = random.choice(TTS_MIX_VOICES)
    elif not re.fullmatch(r"zh-[A-Za-z]+(-[a-z]+)?-[A-Za-z]+Neural", voice):
        voice = "zh-CN-XiaoxiaoNeural"
    key = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()
    path = TTS_CACHE_DIR / f"{key}.mp3"
    if not path.exists() or path.stat().st_size == 0:
        try:
            import edge_tts

            comm = edge_tts.Communicate(text, voice, rate=f"{rate:+d}%")
            await comm.save(str(path))
        except Exception as e:  # noqa: BLE001
            if path.exists():
                path.unlink()
            raise HTTPException(502, f"TTS online lỗi: {e.__class__.__name__}")
    return FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=31536000"})


# ------------------------------------------------------------------ cài đặt

SETTING_KEYS = ["llm_order", "gemini_model", "openai_label", "openai_base_url", "openai_model",
                "tts_source", "tts_voice", "tts_rate", "show_pinyin", "show_vi"]
SECRET_KEYS = ["gemini_api_key", "openai_api_key"]


def _mask(v: str) -> str:
    return ("•" * 8 + v[-4:]) if v else ""


@app.get("/api/settings")
def get_settings():
    s = llm.load_settings()
    with get_db() as db:
        out = {k: get_setting(db, k, s.get(k)) for k in SETTING_KEYS}
    out.setdefault("tts_source", "auto")
    out["tts_source"] = out["tts_source"] or "auto"
    out["tts_voice"] = out["tts_voice"] or "zh-CN-XiaoxiaoNeural"
    out["tts_rate"] = out["tts_rate"] or "-10"
    for k in SECRET_KEYS:
        out[k] = _mask(s.get(k, ""))
        out[f"has_{k}"] = bool(s.get(k))
    out["providers_active"] = llm.configured_providers(s)
    return out


@app.put("/api/settings")
def put_settings(body: dict = Body(...)):
    with get_db() as db:
        for k in SETTING_KEYS:
            if k in body and body[k] is not None:
                set_setting(db, k, str(body[k]).strip())
        for k in SECRET_KEYS:
            v = body.get(k)
            if v is None or v.startswith("•"):
                continue
            set_setting(db, k, v.strip())
    return get_settings()


@app.post("/api/settings/test")
def test_settings(body: dict = Body(...)):
    return llm.test_provider(body.get("provider", "gemini"))


@app.get("/api/settings/gemini-models")
def gemini_models():
    return llm.list_gemini_models()


@app.get("/api/export")
def export_data():
    """Xuất toàn bộ lịch sử (JSON) để sao lưu."""
    with get_db() as db:
        out = {}
        for t in ["books", "units", "vocab", "grammar_points", "unit_progress", "word_mastery", "sessions", "quiz_items",
                  "convos", "turns", "errors", "sentence_reviews", "plan_tasks"]:
            out[t] = rows_to_dicts(db.execute(f"SELECT * FROM {t}").fetchall())
    return JSONResponse(out, headers={"Content-Disposition": "attachment; filename=hanyu-coach-backup.json"})


# ------------------------------------------------------------------ giao diện

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        f = STATIC_DIR / full_path
        if full_path and f.is_file():
            return FileResponse(f)
        # không cache index.html để bản cập nhật hiện ngay (assets đã có hash trong tên)
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})
