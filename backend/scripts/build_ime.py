"""Tạo chỉ mục bộ gõ pinyin -> chữ Hán (ime.sqlite) từ từ điển tần suất của jieba.

Chạy:  python -m scripts.build_ime   (trong thư mục backend)
"""
import re
import sqlite3
import sys
import time
from pathlib import Path

import jieba
from pypinyin import Style, lazy_pinyin, pinyin

OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "ime.sqlite"
CJK = re.compile(r"^[一-鿿]+$")
MIN_FREQ_WORD = 40
MAX_LEN = 4


def main():
    t0 = time.time()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    con = sqlite3.connect(OUT)
    con.execute("CREATE TABLE ime (py TEXT NOT NULL, word TEXT NOT NULL, freq INTEGER NOT NULL)")
    rows = []
    with jieba.get_dict_file() as f:
        for raw in f:
            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            parts = line.split()
            if len(parts) < 2:
                continue
            w, freq = parts[0], int(parts[1])
            if not CJK.match(w) or len(w) > MAX_LEN:
                continue
            if len(w) == 1:
                for p in set(pinyin(w, style=Style.NORMAL, heteronym=True)[0]):
                    rows.append((p.replace("ü", "v"), w, freq))
            elif freq >= MIN_FREQ_WORD:
                py = "".join(lazy_pinyin(w)).replace("ü", "v")
                rows.append((py, w, freq))
    con.executemany("INSERT INTO ime VALUES (?,?,?)", rows)
    con.execute("CREATE INDEX idx_py ON ime(py)")
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"IME: {len(rows)} mục -> {OUT} ({OUT.stat().st_size/1e6:.1f} MB) trong {time.time()-t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
