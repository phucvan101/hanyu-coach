"""Bộ gõ pinyin -> chữ Hán đơn giản, ưu tiên từ người học đã học."""
from __future__ import annotations

import re
import sqlite3
import threading

from pypinyin import lazy_pinyin

from .config import IME_DB_PATH

_local = threading.local()


def _con():
    c = getattr(_local, "con", None)
    if c is None:
        c = sqlite3.connect(f"file:{IME_DB_PATH}?mode=ro", uri=True, check_same_thread=False)
        _local.con = c
    return c


def vocab_index(vocab_hanzi: list[str]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for w in vocab_hanzi:
        py = "".join(lazy_pinyin(w)).replace("ü", "v")
        idx.setdefault(py, []).append(w)
    return idx


def candidates(buf: str, vocab_hanzi: list[str], limit: int = 16) -> list[dict]:
    buf = re.sub(r"[^a-z]", "", (buf or "").lower().replace("ü", "v"))
    if not buf:
        return []
    vocab = set(vocab_hanzi)
    vidx = vocab_index(vocab_hanzi)
    prefixes = [buf[:i] for i in range(len(buf), 0, -1)]
    out: list[dict] = []
    seen: set[str] = set()

    def add(word, py, freq, boost):
        if word in seen:
            return
        seen.add(word)
        consume = len(py) if buf.startswith(py) else len(buf)
        out.append({"word": word, "py": py, "consume": consume, "known": word in vocab, "_s": (boost, freq)})

    # 1) từ đã học khớp chính xác / khớp tiền tố dài nhất
    for p in prefixes:
        for w in vidx.get(p, []):
            add(w, p, 10**9, 3 if p == buf else 2)
    if len(buf) >= 2:
        for p, ws in vidx.items():
            if p.startswith(buf):
                for w in ws:
                    add(w, p, 10**8, 1)

    groups: list[list[dict]] = []
    try:
        con = _con()
        # 2) từ điển chung: khớp chính xác toàn bộ
        rows = con.execute("SELECT py, word, freq FROM ime WHERE py=? ORDER BY freq DESC LIMIT 12", (buf,)).fetchall()
        for py, w, f in rows:
            add(w, py, f, 0.9)
        # 3) khớp tiền tố (gõ liền nhiều âm tiết)
        ph = ",".join("?" * len(prefixes[1:]))
        if ph:
            rows = con.execute(
                f"SELECT py, word, freq FROM ime WHERE py IN ({ph}) ORDER BY length(py) DESC, freq DESC LIMIT 20",
                prefixes[1:],
            ).fetchall()
            for py, w, f in rows:
                add(w, py, f, 0.5 + len(py) / 100)
        # 4) gợi ý hoàn thành
        if len(buf) >= 3:
            rows = con.execute(
                "SELECT py, word, freq FROM ime WHERE py > ? AND py < ? ORDER BY freq DESC LIMIT 6",
                (buf, buf + "{"),
            ).fetchall()
            for py, w, f in rows:
                add(w, py, f, 0.2)
    except sqlite3.Error:
        pass

    out.sort(key=lambda x: x["_s"], reverse=True)
    for o in out:
        o.pop("_s", None)
    return out[:limit]
