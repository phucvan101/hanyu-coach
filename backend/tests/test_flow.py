"""Test luồng đầy đủ với LLM giả lập.  Chạy: HANYU_FAKE_LLM=1 pytest -q  (trong thư mục backend)"""
import os
import tempfile
import time
from pathlib import Path

os.environ["HANYU_FAKE_LLM"] = "1"
os.environ["HANYU_DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLE = Path(__file__).parent / "sample_vocab.csv"


def _wait_ready(c, book_id):
    for _ in range(100):
        b = c.get(f"/api/books/{book_id}").json()
        if b["status"] != "importing":
            return b
        time.sleep(0.1)
    raise AssertionError("import timeout")


def test_full_flow():
    with TestClient(app) as c:
        r = c.post("/api/books/import", files={"file": ("quyen1.csv", SAMPLE.read_bytes(), "text/csv")})
        assert r.status_code == 200, r.text
        book = _wait_ready(c, r.json()["id"])
        assert book["status"] == "ready", book
        assert book["units"], "phải có bài"
        total = sum(len(u["words"]) for u in book["units"])
        assert total == r.json()["word_count"]

        # bộ gõ
        cands = c.get("/api/ime", params={"q": "fan"}).json()
        assert cands and cands[0]["word"] in ("饭", "房间")

        dash = c.get("/api/dashboard").json()
        rec = dash["recommend"]
        assert rec["stage"] == "vocab"

        # hội thoại bị khoá khi chưa qua từ vựng
        r = c.post("/api/sessions", json={"unit_id": rec["unit_id"], "stage": "controlled"})
        assert r.status_code == 400

        st = c.post("/api/sessions", json={}).json()
        sid = st["session"]["id"]
        st = c.post(f"/api/sessions/{sid}/quiz/start").json()
        items = st["quiz_items"]
        assert items and all(not i["answered"] for i in items)
        # trả lời đúng hết bằng cách đọc đáp án từ DB
        from app.db import get_db
        import json
        with get_db() as db:
            ans = {r["id"]: json.loads(r["answer"])["value"] for r in db.execute("SELECT id, answer FROM quiz_items WHERE session_id=?", (sid,))}
        for it in items:
            res = c.post(f"/api/quiz-items/{it['id']}/answer", json={"answer": ans[it["id"]]}).json()
            assert res["correct"], (it, res)
        fin = c.post(f"/api/sessions/{sid}/quiz/finish").json()
        assert fin["score"] == 100 and fin["passed"]

        cv = c.post(f"/api/sessions/{sid}/convo", json={"stage": "controlled"}).json()
        assert cv["turns"][0]["role"] == "ai" and cv["turns"][0]["pinyin"]
        for text in ["我想吃饺子", "我很是高兴", "wo xiang he cha", "谢谢你"]:
            cv = c.post(f"/api/convos/{cv['id']}/message", json={"text": text}).json()
        assert cv["user_turns"] == 4
        modes = [t["input_mode"] for t in cv["turns"] if t["role"] == "user"]
        assert modes[2] == "pinyin"
        fin = c.post(f"/api/convos/{cv['id']}/finish").json()
        assert fin["score"] > 0

        rep = c.post(f"/api/sessions/{sid}/finish").json()
        assert rep["skills"] and rep["ai"]["strengths"]
        assert rep["sentence_errors"], "câu sai phải được ghi lại"

        # buổi sau: câu sai được ôn lại
        st2 = c.post("/api/sessions", json={"unit_id": rec["unit_id"], "stage": "controlled"}).json()
        assert st2["sentence_reviews"], "phải ôn câu sai cũ"
        sr = st2["sentence_reviews"][0]
        res = c.post(f"/api/sentence-reviews/{sr['id']}/answer", json={"answer": "我很高兴。"}).json()
        assert res["correct"]

        dash = c.get("/api/dashboard").json()
        assert dash["history"] and dash["streak"] >= 1
        words = c.get("/api/words").json()
        assert any(w["level"] != "new" for w in words)


def test_pinyin_drill():
    with TestClient(app) as c:
        r = c.post("/api/books/import", files={"file": ("quyen-drill.csv", SAMPLE.read_bytes(), "text/csv")})
        _wait_ready(c, r.json()["id"])
        o = c.get("/api/drill/pinyin/options").json()
        assert o["counts"]["all"] > 0 and o["books"]
        unit = o["books"][-1]["units"][0]
        deck = c.post("/api/drill/pinyin/deck", json={"scope": "unit", "id": unit["id"], "limit": 0}).json()
        assert len(deck) == unit["word_count"] and "pinyin" not in deck[0]
        deck = c.post("/api/drill/pinyin/deck", json={"scope": "all", "limit": 5}).json()
        assert len(deck) == 5
        from app.db import get_db
        from app.pinyin_utils import normalize_letters
        w = deck[0]
        with get_db() as db:
            py = db.execute("SELECT pinyin FROM vocab WHERE id=?", (w["vocab_id"],)).fetchone()["pinyin"]
        res = c.post(f"/api/drill/pinyin/{w['vocab_id']}/check", json={"answer": py}).json()
        assert res["correct"] and not res["tone_warning"], res
        res = c.post(f"/api/drill/pinyin/{w['vocab_id']}/check", json={"answer": normalize_letters(py)}).json()
        assert res["correct"] and res["tone_warning"] == "missing"
        res = c.post(f"/api/drill/pinyin/{deck[1]['vocab_id']}/check", json={"answer": ""}).json()
        assert not res["correct"]
        assert c.get("/api/drill/pinyin/options").json()["counts"]["weak"] >= 1
        assert c.post("/api/drill/pinyin/999999/check", json={"answer": "a"}).status_code == 404


def test_flashcards():
    with TestClient(app) as c:
        r = c.post("/api/books/import", files={"file": ("quyen-flash.csv", SAMPLE.read_bytes(), "text/csv")})
        _wait_ready(c, r.json()["id"])
        deck = c.post("/api/flashcards/deck", json={"scope": "all", "limit": 4}).json()
        assert len(deck) == 4 and deck[0]["pinyin"] and "meaning" in deck[0]
        easy = c.post(f"/api/flashcards/{deck[0]['vocab_id']}/rate", json={"rating": 4}).json()
        assert easy["interval_days"] >= 1
        c.post(f"/api/flashcards/{deck[1]['vocab_id']}/rate", json={"rating": 1})
        weak = c.post("/api/flashcards/deck", json={"scope": "weak", "limit": 0}).json()
        assert any(w["vocab_id"] == deck[1]["vocab_id"] for w in weak)
        assert c.post(f"/api/flashcards/{deck[0]['vocab_id']}/rate", json={"rating": 7}).status_code == 400
        assert c.post("/api/flashcards/999999/rate", json={"rating": 3}).status_code == 404


def test_book_convo_and_plan():
    with TestClient(app) as c:
        r = c.post("/api/books/import", files={"file": ("quyen-tonghop.csv", SAMPLE.read_bytes(), "text/csv")})
        book = _wait_ready(c, r.json()["id"])
        assert c.post("/api/book-sessions", json={"book_id": book["id"], "topic": " "}).status_code == 400
        st = c.post("/api/book-sessions", json={"book_id": book["id"], "topic": "Đi uống cà phê cuối tuần", "max_turns": 6}).json()
        sid = st["session"]["id"]
        assert st["session"]["start_stage"] == "book" and not st["review_items"] and st["book"]["id"] == book["id"]
        cv = c.post(f"/api/sessions/{sid}/convo", json={"stage": "book"}).json()
        assert cv["stage"] == "book" and cv["max_turns"] == 6 and len(cv["target_words"]) == 12
        first = cv["turns"][0]
        assert [n["hanzi"] for n in first["notes"]] == ["拿铁"] and first["notes"][0]["meaning_vi"], first
        for text in ["我想吃饺子", "我很是高兴", "谢谢你", "我很是忙"]:
            cv = c.post(f"/api/convos/{cv['id']}/message", json={"text": text}).json()
        # AI dùng từ mới mà không giải thích -> app tự hỏi nghĩa
        ai_notes = [n for t in cv["turns"] if t["role"] == "ai" for n in t["notes"] if n["hanzi"] == "超市"]
        assert ai_notes and all(n["meaning_vi"] == "nghĩa của 超市" for n in ai_notes), ai_notes
        # lượt cũ còn trống nghĩa -> endpoint bổ sung
        from app.db import get_db
        with get_db() as db:
            tid = db.execute("SELECT id FROM turns WHERE convo_id=? AND role='ai' ORDER BY id DESC LIMIT 1", (cv["id"],)).fetchone()["id"]
            db.execute("UPDATE turns SET notes=? WHERE id=?", ('[{"hanzi": "超市", "pinyin": "chāoshì", "meaning_vi": "", "explain_vi": ""}]', tid))
        cv = c.post(f"/api/convos/{cv['id']}/explain-notes").json()
        assert next(t for t in cv["turns"] if t["id"] == tid)["notes"][0]["meaning_vi"] == "nghĩa của 超市"
        user_turns = [t for t in cv["turns"] if t["role"] == "user"]
        assert user_turns[1]["eval"]["errors"], "câu sai phải có nhận xét ngay"
        fin = c.post(f"/api/convos/{cv['id']}/finish").json()
        assert fin["progress"] is None and fin["score"] > 0

        rep = c.post(f"/api/sessions/{sid}/finish").json()
        assert rep["mode"] == "book" and rep["topic"] and rep["sentence_errors"]
        assert [n["hanzi"] for n in rep["new_words"]] == ["拿铁", "超市"] and all(n["meaning_vi"] for n in rep["new_words"])
        st = c.get(f"/api/sessions/{sid}").json()
        kinds = [t["kind"] for t in st["plan_tasks"]]
        assert kinds[0] == "rewrite" and "grammar_convo" in kinds and "pinyin_drill" in kinds, kinds

        # nhiệm vụ viết lại câu sai
        rw = next(t for t in st["plan_tasks"] if t["kind"] == "rewrite")
        rw = c.get(f"/api/plan-tasks/{rw['id']}").json()
        assert rw["items"] and "corrected" not in rw["items"][0]
        res = c.post(f"/api/errors/{rw['items'][0]['id']}/rewrite", json={"answer": "我很高兴。"}).json()
        assert res["correct"] and res["corrected"]
        assert c.post(f"/api/plan-tasks/{rw['id']}/complete", json={"score": 100}).json()["status"] == "done"

        # nhiệm vụ ôn pinyin có sẵn bộ thẻ
        dr = next(t for t in st["plan_tasks"] if t["kind"] == "pinyin_drill")
        assert c.get(f"/api/plan-tasks/{dr['id']}").json()["items"]

        # nhiệm vụ hội thoại ngữ pháp: chạy một buổi mini, xong thì tự đánh dấu hoàn thành
        gt = next(t for t in st["plan_tasks"] if t["kind"] == "grammar_convo")
        run = c.post(f"/api/plan-tasks/{gt['id']}/start").json()
        rsid = run["session_id"]
        st2 = c.get(f"/api/sessions/{rsid}").json()
        assert st2["task"]["id"] == gt["id"] and st2["session"]["focus"]["grammar"]
        cv2 = c.post(f"/api/sessions/{rsid}/convo", json={"stage": "book"}).json()
        cv2 = c.post(f"/api/convos/{cv2['id']}/message", json={"text": "我很高兴"}).json()
        c.post(f"/api/convos/{cv2['id']}/finish")
        assert c.get(f"/api/plan-tasks/{gt['id']}").json()["status"] == "done"
        c.post(f"/api/sessions/{rsid}/finish")
        assert not c.get(f"/api/sessions/{rsid}").json()["plan_tasks"], "buổi chạy nhiệm vụ không sinh lộ trình mới"
        assert len(c.get("/api/plan-tasks", params={"status": "open"}).json()) >= 1
        hist = c.get("/api/sessions").json()
        assert any(h["title_vi"].startswith("Tổng hợp:") for h in hist)
