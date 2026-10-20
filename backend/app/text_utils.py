"""Tách từ (jieba) và kiểm tra câu của AI chỉ dùng từ đã học (whitelist)."""
from __future__ import annotations

import logging
import re
import threading

import jieba

jieba.setLogLevel(logging.WARNING)

CJK_RE = re.compile(r"[㐀-鿿豈-﫿]")
_lock = threading.Lock()
_added: set[str] = set()

# Từ nền tảng luôn được phép dùng (đại từ, trợ từ, số đếm, chào hỏi... mức HSK1)
BASE_WORDS = """
我 你 他 她 它 我们 你们 他们 她们 咱们 大家 自己 的 地 得 了 着 过 吗 呢 吧 啊 呀 哦 嗯 喂 哈
是 不 没 没有 有 在 很 也 都 和 跟 好 这 那 这个 那个 这些 那些 个 一 二 三 四 五 六 七 八 九 十 零
百 千 万 两 几 多 少 大 小 人 什么 怎么 谁 哪 哪儿 这儿 那儿 哪里 这里 那里 要 想 会 能 可以 去 来 说 看 听
吃 喝 买 卖 叫 就 还 再 太 真 非常 欢迎 请 谢谢 对不起 没关系 不客气 再见 你好 您好 您 先生 小姐
号 月 日 年 点 分 块 毛 元 今天 明天 昨天 现在 时候 东西 朋友 名字 家 学生 老师 中国 越南 汉语 中文 语
做 工作 学习 喜欢 知道 认识 觉得 给 对 错 一下 一点儿 一些 一起 最 更 比 还是 或者 因为 所以 但是 可是 如果
上 下 里 外 前 后 左 右 边 上边 下边 里边 外边 前边 后边 旁边 早上 上午 中午 下午 晚上 天 星期 岁 本 杯 碗 件 张 位 只 条 瓶 辆
妈妈 爸爸 哥哥 姐姐 弟弟 妹妹 儿子 女儿 男 女 水 饭 菜 茶 钱 书 车 门 路 吗 嘛 哎 唉 好的 好吧 对了 当然 怎么样 为什么
""".split()


def ensure_words(words) -> None:
    """Thêm từ của người học vào từ điển jieba để tách từ chính xác."""
    with _lock:
        for w in words:
            if w and w not in _added and CJK_RE.search(w):
                jieba.add_word(w, freq=20000)
                _added.add(w)


def segment_words(text: str) -> list[str]:
    return [t for t in jieba.lcut(text or "", HMM=False) if t]


def build_whitelist(vocab_hanzi) -> set[str]:
    wl = set(BASE_WORDS)
    wl.update(vocab_hanzi)
    ensure_words(vocab_hanzi)
    return wl


def out_of_vocab(text: str, whitelist: set[str], ignore: set[str] | None = None) -> list[str]:
    """Danh sách từ ngoài vốn đã học trong câu.

    Một token được chấp nhận nếu: nằm trong whitelist, hoặc mọi chữ của nó đều là
    từ một chữ có trong whitelist, hoặc là số.
    """
    ignore = ignore or set()
    single = {w for w in whitelist if len(w) == 1}
    bad = []
    for tok in segment_words(text):
        if not CJK_RE.search(tok):
            continue
        if tok in whitelist or tok in ignore:
            continue
        if all((c in single) or not CJK_RE.match(c) for c in tok):
            continue
        for part in _uncovered(tok, whitelist):
            if part not in bad and part not in ignore:
                bad.append(part)
    return bad


def _uncovered(tok: str, whitelist: set[str]) -> list[str]:
    """Phần của token không ghép được từ các từ trong whitelist (khớp dài nhất)."""
    out, run, i = [], "", 0
    while i < len(tok):
        for j in range(min(len(tok), i + 6), i, -1):
            if tok[i:j] in whitelist:
                if run:
                    out.append(run)
                    run = ""
                i = j
                break
        else:
            run += tok[i]
            i += 1
    if run:
        out.append(run)
    return out or [tok]


def words_used(text: str, targets: list[str]) -> list[str]:
    t = text or ""
    return [w for w in targets if w and w in t]


def strip_cjk_punct(text: str) -> str:
    return re.sub(r"[\s，。？！、；：,.?!;:\"'“”‘’（）()…—\-]", "", text or "")
