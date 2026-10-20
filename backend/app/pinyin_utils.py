"""Chuẩn hoá & chấm pinyin.

- Người học có thể gõ: dấu thanh (nǐhǎo), số (ni3hao3), không dấu (nihao), có/không dấu cách.
- Chấm theo "âm" (chữ cái) là chính; thanh điệu sai/thiếu chỉ cảnh báo.
- Đáp án đúng chấp nhận cả pinyin trong file dữ liệu lẫn pinyin do pypinyin sinh ra
  (dữ liệu Hanzii đôi khi không đồng nhất: viết hoa, dấu cách, thanh nhẹ...).
"""
from __future__ import annotations

import re
from functools import lru_cache

from pypinyin import Style, pinyin
from pypinyin.contrib.tone_convert import to_normal
from pypinyin.pinyin_dict import pinyin_dict

_MARKS = {
    "ā": ("a", 1), "á": ("a", 2), "ǎ": ("a", 3), "à": ("a", 4),
    "ē": ("e", 1), "é": ("e", 2), "ě": ("e", 3), "è": ("e", 4),
    "ī": ("i", 1), "í": ("i", 2), "ǐ": ("i", 3), "ì": ("i", 4),
    "ō": ("o", 1), "ó": ("o", 2), "ǒ": ("o", 3), "ò": ("o", 4),
    "ū": ("u", 1), "ú": ("u", 2), "ǔ": ("u", 3), "ù": ("u", 4),
    "ǖ": ("v", 1), "ǘ": ("v", 2), "ǚ": ("v", 3), "ǜ": ("v", 4), "ü": ("v", 0),
    "ń": ("n", 2), "ň": ("n", 3), "ǹ": ("n", 4), "ḿ": ("m", 2),
    "ê": ("e", 0),
}

CJK_RE = re.compile(r"[㐀-鿿豈-﫿]")


@lru_cache(maxsize=1)
def syllables() -> frozenset:
    s = set()
    for v in pinyin_dict.values():
        for p in v.split(","):
            n = to_normal(p.strip())
            if n and n.isalpha():
                s.add(n.lower())
    s.update({"r", "er", "ng", "hm", "m", "n"})
    return frozenset(s)


class Stream:
    """Chuỗi chữ cái + thông tin thanh điệu gắn theo vị trí."""

    def __init__(self, text: str):
        self.letters: list[str] = []
        self.mark: dict[int, int] = {}
        self.digit_after: dict[int, int] = {}
        t = (text or "").strip().lower().replace("u:", "v")
        for ch in t:
            if ch in _MARKS:
                base, tone = _MARKS[ch]
                if tone:
                    self.mark[len(self.letters)] = tone
                self.letters.append(base)
            elif "a" <= ch <= "z":
                self.letters.append(ch)
            elif ch in "012345" and self.letters:
                d = int(ch)
                self.digit_after[len(self.letters) - 1] = 5 if d in (0, 5) else d
            # các ký tự khác (dấu cách, ', -, dấu câu) bỏ qua

    @property
    def word(self) -> str:
        return "".join(self.letters)

    def tone_in(self, a: int, b: int) -> int:
        for i in range(a, b):
            if i in self.mark:
                return self.mark[i]
        return self.digit_after.get(b - 1, 0)

    @property
    def has_any_tone(self) -> bool:
        return bool(self.mark or self.digit_after)


def segment(letters: str) -> list[tuple[int, int]] | None:
    """Tách chuỗi chữ cái thành âm tiết hợp lệ (ít âm tiết nhất)."""
    n = len(letters)
    syl = syllables()
    best: list = [None] * (n + 1)
    best[n] = []
    for i in range(n - 1, -1, -1):
        cand = None
        for j in range(min(n, i + 6), i, -1):
            if letters[i:j] in syl and best[j] is not None:
                path = [(i, j)] + best[j]
                if cand is None or len(path) < len(cand):
                    cand = path
        best[i] = cand
    return best[0]


def parse(text: str, neutral_default: int = 0) -> list[tuple[str, int]] | None:
    st = Stream(text)
    w = st.word
    seg = segment(w)
    if seg is None:
        return None
    out = []
    for a, b in seg:
        t = st.tone_in(a, b)
        out.append((w[a:b], t if t else neutral_default))
    return out


@lru_cache(maxsize=4096)
def _pypinyin_form(hanzi: str) -> tuple:
    res = []
    for item in pinyin(hanzi, style=Style.TONE3, neutral_tone_with_five=True, errors="ignore"):
        p = item[0].lower()
        m = re.match(r"^([a-zü]+)([1-5])?$", p)
        if not m:
            continue
        res.append((m.group(1).replace("ü", "v"), int(m.group(2) or 5)))
    if len(hanzi) > 1 and hanzi.endswith("儿") and res and res[-1][0] == "er":
        res[-1] = ("er", 5)
    return tuple(res)


def expected_forms(hanzi: str, data_pinyin: str) -> list[list[tuple[str, int]]]:
    forms = []
    if data_pinyin:
        f = parse(data_pinyin, neutral_default=5)
        if f:
            forms.append(f)
    pf = list(_pypinyin_form(hanzi)) if hanzi else []
    if pf and pf not in forms:
        forms.append(pf)
    return forms


def _cmp_letters(a: str, b: str) -> str | None:
    if a == b:
        return "exact"
    if a.replace("v", "u") == b.replace("v", "u"):
        return "umlaut"
    return None


def check_pinyin(user: str, hanzi: str, data_pinyin: str) -> dict:
    """Trả về {correct, tone_status, warning, expected}.

    correct: đúng âm (không xét thanh).
    tone_status: ok | missing | mismatch | n/a
    """
    st = Stream(user)
    uw = st.word
    result = {"correct": False, "tone_status": "n/a", "warning": None, "expected": data_pinyin}
    if not uw:
        return result
    best = None
    rank = {"ok": 3, "missing": 2, "mismatch": 1}
    for form in expected_forms(hanzi, data_pinyin):
        fw = "".join(s for s, _ in form)
        how = _cmp_letters(uw, fw)
        if not how:
            continue
        pos = 0
        statuses = []
        wrong_syl = []
        for i, (syl, exp) in enumerate(form):
            a, b = pos, pos + len(syl)
            pos = b
            ut = st.tone_in(a, b)
            last_of_multi = len(form) > 1 and i == len(form) - 1
            if exp == 5 or (last_of_multi and ut in (0, 5) and st.has_any_tone):
                # thanh nhẹ: chấp nhận mọi cách ghi; âm tiết cuối của từ ghép có thể đọc nhẹ
                statuses.append("ok")
            elif exp == 5:
                statuses.append("ok")
            elif ut == 0:
                statuses.append("missing")
            elif ut == exp:
                statuses.append("ok")
            else:
                statuses.append("mismatch")
                wrong_syl.append(syl)
        if not st.has_any_tone:
            status = "missing"
        elif "mismatch" in statuses:
            status = "mismatch"
        elif "missing" in statuses:
            status = "missing"
        else:
            status = "ok"
        cand = {"status": status, "how": how, "wrong": wrong_syl}
        if best is None or rank[status] > rank[best["status"]]:
            best = cand
    if best is None:
        return result
    result["correct"] = True
    result["tone_status"] = best["status"]
    warnings = []
    if best["how"] == "umlaut":
        warnings.append("Chú ý: âm ü (gõ là v hoặc ü), không phải u.")
    if best["status"] == "missing":
        warnings.append("Đúng âm nhưng chưa ghi thanh điệu.")
    elif best["status"] == "mismatch":
        warnings.append("Đúng âm nhưng sai thanh điệu" + (f" ở: {', '.join(best['wrong'])}." if best["wrong"] else "."))
    result["warning"] = " ".join(warnings) or None
    return result


def is_latin_input(text: str) -> bool:
    t = (text or "").strip()
    if not t or CJK_RE.search(t):
        return False
    letters = sum(1 for c in t if c.isalpha())
    return letters >= max(1, len(t) * 0.5)


_PUNCT = {"，": ",", "。": ".", "？": "?", "！": "!", "、": ",", "；": ";", "：": ":", "“": '"', "”": '"', "（": "(", "）": ")", "…": "…"}


def to_display_pinyin(text: str) -> str:
    """Pinyin có dấu cho câu tiếng Trung, tách theo từ (jieba)."""
    from .text_utils import segment_words

    out: list[str] = []
    for tok in segment_words(text):
        if CJK_RE.search(tok):
            syls = [x[0] for x in pinyin(tok, style=Style.TONE, errors=lambda c: list(c))]
            if len(tok) > 1 and tok.endswith("儿") and len(syls) > 1 and syls[-1] in ("ér", "er"):
                syls = syls[:-1]
                syls[-1] = syls[-1] + "r"
            out.append("".join(syls))
        elif tok.strip():
            t = "".join(_PUNCT.get(c, c) for c in tok.strip())
            if out and all(c in ",.?!;:…" for c in t):
                out[-1] = out[-1] + t
            else:
                out.append(t)
    return " ".join(out)


def normalize_letters(text: str) -> str:
    return Stream(text).word
