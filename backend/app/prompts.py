"""Các prompt gửi LLM. Tất cả đều yêu cầu trả về JSON."""
from __future__ import annotations

import json

TEACHER = (
    "Bạn là giáo viên tiếng Trung giàu kinh nghiệm, dạy người Việt Nam. "
    "Giải thích bằng tiếng Việt ngắn gọn, thân thiện. Tiếng Trung luôn dùng chữ giản thể."
)

# ---------------------------------------------------------------- import

ENRICH_SYSTEM = TEACHER + """
Nhiệm vụ: chuẩn hoá danh sách từ vựng (lấy từ từ điển Hanzii nên nghĩa đầu tiên thường là nghĩa hiếm).
Với MỖI từ, trả về:
- "hanzi": giữ nguyên
- "primary_meaning": nghĩa tiếng Việt thông dụng nhất trong giáo trình sơ cấp, NGẮN (tối đa 6 chữ).
  Ví dụ: 错 → "sai", 东西 → "đồ vật, đồ", 才 → "mới (thì mới)", 点 → "giờ; gọi (món)", 做 → "làm", 奶 → "sữa", 刚 → "vừa mới".
- "is_function_word": true nếu là hư từ/từ ngữ pháp (trợ từ, giới từ, phó từ ngữ pháp: 了 吧 呢 把 都 也 还 再 才 就 给 对 在...), ngược lại false.
- "usage_vi": với hư từ: mô tả cách dùng ngắn (VD 吧: "cuối câu, đề nghị/phỏng đoán: ...nhé, ...chắc"); từ thường: "".
- "example_zh": 1 câu ví dụ rất đơn giản (≤ 12 chữ Hán) có chứa đúng từ đó, chỉ dùng từ cơ bản.
- "example_vi": nghĩa tiếng Việt của câu ví dụ.
Trả JSON: {"words": [ {...}, ... ]} theo đúng thứ tự đầu vào, không bỏ sót từ nào."""


def enrich_user(words: list[dict]) -> str:
    lines = [f"{w['hanzi']} | {w['pinyin']} | {'; '.join(w['meanings'][:6])}" for w in words]
    return "Danh sách (hanzi | pinyin | nghĩa từ điển):\n" + "\n".join(lines)


GROUP_SYSTEM = TEACHER + """
Nhiệm vụ: chia danh sách từ vựng (người học đã học xong cả quyển) thành các BÀI (unit) theo CHỦ ĐỀ GIAO TIẾP đời sống,
để luyện: kiểm tra từ vựng → hội thoại nhập vai.
Quy tắc:
- Mỗi bài 10–20 từ. Mỗi từ thuộc ĐÚNG MỘT bài. Không được bỏ sót hay thêm từ ngoài danh sách.
- Gom theo tình huống dùng được trong hội thoại (VD: Chào hỏi & làm quen; Gọi món ở quán ăn; Mua sắm & mặc cả;
  Hỏi đường & phương tiện; Trường lớp; Công việc & nghề nghiệp; Thời gian & hẹn gặp; Sức khoẻ; Quốc gia & ngôn ngữ...).
- Hư từ (了 吧 呢 都 也...) chia đều vào các bài phù hợp.
- Với mỗi bài, viết tình huống nhập vai cụ thể cho AI đóng một vai và người học đóng một vai.
Trả JSON:
{"units": [{"title_vi": "Gọi món ở quán ăn", "title_zh": "在饭馆点菜",
  "scenario_vi": "Bạn vào một quán ăn nhỏ ở Bắc Kinh và gọi món.",
  "ai_role_vi": "Nhân viên phục vụ", "user_role_vi": "Khách hàng",
  "words": ["点菜", "饺子", ...]}]}"""


def group_user(words: list[dict]) -> str:
    lines = [f"{w['hanzi']} ({w.get('primary_meaning') or w['meanings'][0]})" for w in words]
    return f"Tổng {len(words)} từ:\n" + "\n".join(lines)


GRAMMAR_SYSTEM = TEACHER + """
Nhiệm vụ: đọc tài liệu bài học (ngữ pháp / bài khoá) và rút ra các ĐIỂM NGỮ PHÁP và MẪU CÂU quan trọng.
Mỗi điểm gồm: "pattern" (mẫu câu, VD "主语 + 在 + 地点 + 动词"), "explanation_vi" (giải thích ngắn),
"example_zh" (1 câu ví dụ), "example_vi".
Tối đa 40 điểm, ưu tiên mẫu dùng nhiều trong giao tiếp. Trả JSON: {"grammar_points": [ ... ]}"""


def grammar_user(text: str) -> str:
    return "Tài liệu:\n" + text[:30000]


# ---------------------------------------------------------------- hội thoại

def _vocab_block(allowed: list[str] | None, targets: list[dict], grammar: list[dict]) -> str:
    parts = []
    tw = ", ".join(f"{t['hanzi']} ({t['meaning']})" for t in targets)
    parts.append(f"TỪ MỤC TIÊU của bài (cần tạo cơ hội cho người học dùng): {tw}")
    if allowed is not None:
        parts.append("DANH SÁCH TỪ ĐƯỢC PHÉP (vốn từ người học đã học – chỉ được dùng các từ này, "
                     "cộng thêm tên riêng và số): " + " ".join(allowed))
    if grammar:
        g = "; ".join(f"{x['pattern']}" + (f" (VD: {x['example_zh']})" if x.get("example_zh") else "") for x in grammar[:15])
        parts.append("MẪU CÂU / NGỮ PHÁP người học đã học (hãy dùng và gợi cho người học dùng): " + g)
    return "\n".join(parts)


def convo_system(stage: str, unit: dict, allowed: list[str] | None, targets: list[dict], grammar: list[dict]) -> str:
    if stage == "controlled":
        mode = (
            "GIAI ĐOẠN: HỘI THOẠI CÓ KIỂM SOÁT.\n"
            "- Câu của bạn PHẢI chỉ dùng từ trong DANH SÁCH TỪ ĐƯỢC PHÉP. Câu ngắn (≤ 15 chữ Hán), rõ ràng.\n"
            "- Mỗi lượt chỉ 1–2 câu, kết thúc bằng một câu hỏi đơn giản để người học trả lời bằng TỪ MỤC TIÊU.\n"
        )
    else:
        mode = (
            "GIAI ĐOẠN: HỘI THOẠI TỰ DO THEO CHỦ ĐỀ.\n"
            "- Dùng tiếng Trung đơn giản (HSK 1–3), tự nhiên như người bản xứ nói chậm. Mỗi lượt 1–3 câu.\n"
            "- Mở rộng tình huống, đặt câu hỏi mở để người học phải tự diễn đạt, ưu tiên gợi các TỪ MỤC TIÊU chưa dùng.\n"
        )
    return (
        TEACHER + "\n"
        f"Bạn đóng vai: {unit.get('ai_role_vi') or 'người bản xứ'}. Người học đóng vai: {unit.get('user_role_vi') or 'chính mình'}.\n"
        f"Tình huống: {unit.get('scenario_vi') or unit.get('title_vi')}\n"
        + mode +
        "- Luôn giữ vai, KHÔNG giảng bài trong câu thoại. Phần sửa lỗi đặt ở trường evaluation.\n"
        + _vocab_block(allowed, targets, grammar)
    )


NEW_WORDS_FIELD = (
    ', "new_words": [{"hanzi": "từ ngoài DANH SÁCH TỪ ĐƯỢC PHÉP có trong câu đáp", "pinyin": "có dấu",'
    ' "meaning_vi": "nghĩa ngắn", "explain_vi": "giải thích ngắn cách dùng / vì sao cần từ này"}]'
)


def convo_open_user(new_words: bool = False) -> str:
    nw = NEW_WORDS_FIELD if new_words else ""
    return (
        "Bắt đầu hội thoại. Trả JSON:\n"
        '{"intro_vi": "1–2 câu tiếng Việt giới thiệu tình huống và nhiệm vụ của người học",'
        ' "reply": {"hanzi": "câu mở đầu của bạn (tiếng Trung)", "vi": "nghĩa tiếng Việt"' + nw + '}}'
    )


def convo_turn_user(history: list[dict], user_text: str, input_mode: str, remaining_targets: list[str], turns_left: int,
                    new_words: bool = False) -> str:
    h = "\n".join(f"{'AI' if t['role'] == 'ai' else 'Người học'}: {t['hanzi'] or t['raw_text']}" for t in history[-16:])
    mode_note = {
        "pinyin": "Người học gõ bằng PINYIN (có thể thiếu dấu). Hãy chuyển sang chữ Hán đúng ý họ định nói (giữ nguyên lỗi ngữ pháp nếu có) trong user_hanzi.",
        "voice": "Câu của người học được nhận dạng từ giọng nói, có thể sai vài chữ đồng âm; hiểu theo ngữ cảnh, không bắt lỗi chữ do nhận dạng.",
        "hanzi": "Người học gõ chữ Hán.",
    }.get(input_mode, "")
    end_note = "Đây là lượt cuối: kết thúc hội thoại tự nhiên, should_end = true." if turns_left <= 1 else ""
    nw = NEW_WORDS_FIELD if new_words else ""
    return f"""Hội thoại tới giờ:
{h}

Câu mới của người học: {user_text}
({mode_note})
Từ mục tiêu chưa được người học dùng: {', '.join(remaining_targets) or '(đã dùng hết)'}
{end_note}

Hãy (1) đánh giá câu của người học, (2) đáp lại trong vai. Trả JSON:
{{
 "user_hanzi": "câu của người học bằng chữ Hán (giữ nguyên lỗi)",
 "evaluation": {{
   "score": 0-100,               // tổng thể: đúng ngữ pháp, dùng từ đúng, phù hợp ngữ cảnh
   "grammar_score": 0-100,
   "is_correct": true/false,     // true nếu không có lỗi đáng kể
   "corrected": "câu đúng & tự nhiên nhất (chữ Hán)",
   "corrected_vi": "nghĩa tiếng Việt",
   "errors": [{{"type": "ngu_phap|tu_vung|trat_tu|luong_tu|tro_tu|chinh_ta|khong_phu_hop",
                "original": "phần sai", "correction": "phần sửa",
                "grammar_point": "tên điểm ngữ pháp (VD: 了 chỉ hoàn thành)", "explanation_vi": "giải thích ngắn"}}],
   "hint_vi": "1 câu gợi ý nhẹ nhàng (nếu sai) hoặc khen cụ thể (nếu đúng)",
   "used_words": ["từ mục tiêu người học dùng ĐÚNG trong câu này"],
   "vietnamese_only": true/false // true nếu người học chỉ nói tiếng Việt/không dùng tiếng Trung
 }},
 "reply": {{"hanzi": "câu đáp của bạn", "vi": "nghĩa tiếng Việt"{nw}}},
 "should_end": false
}}
Nếu người học nói tiếng Việt: score thấp, corrected là cách nói bằng tiếng Trung, vẫn tiếp tục hội thoại."""


MAX_NEW_WORDS = 2


def book_convo_system(book_title: str, topic: str, allowed: list[str], targets: list[dict], grammar: list[dict],
                      focus: dict | None = None) -> str:
    focus = focus or {}
    parts = [
        TEACHER,
        "GIAI ĐOẠN: HỘI THOẠI TỔNG HỢP CẢ QUYỂN.",
        f"Người học đã học xong quyển \"{book_title}\" và tự chọn chủ đề: \"{topic}\".",
        "Bạn là người bản xứ thân thiện trò chuyện theo chủ đề này; nếu chủ đề cần, hãy tự nhận một vai phù hợp và giữ vai.",
        "- Ưu tiên tuyệt đối từ trong DANH SÁCH TỪ ĐƯỢC PHÉP (vốn từ người học). Câu ngắn (≤ 20 chữ Hán), mỗi lượt 1–3 câu,"
        " kết thúc bằng một câu hỏi mở để người học phải tự nói.",
        f"- Chỉ khi chủ đề thật sự cần, được dùng TỐI ĐA {MAX_NEW_WORDS} từ ngoài danh sách mỗi lượt. MỌI từ ngoài danh sách"
        " phải được liệt kê trong reply.new_words kèm pinyin, nghĩa và giải thích ngắn.",
        "- Tạo cơ hội để người học dùng các TỪ MỤC TIÊU; đổi hướng câu chuyện sang các từ mục tiêu chưa dùng.",
        "- Đánh giá câu của người học kỹ: mọi lỗi ngữ pháp, dùng từ, trật tự từ, lượng từ, câu không tự nhiên đều phải sửa.",
        "- Luôn giữ vai trong câu thoại, KHÔNG giảng bài trong câu thoại. Phần sửa lỗi đặt ở trường evaluation.",
    ]
    if focus.get("grammar"):
        parts.append("TRỌNG TÂM BUỔI NÀY (người học từng sai, hãy tạo nhiều tình huống buộc phải dùng và chấm chặt): "
                     + "; ".join(focus["grammar"]))
    if focus.get("note_vi"):
        parts.append("Ghi chú: " + focus["note_vi"])
    parts.append(_vocab_block(allowed, targets, grammar))
    return "\n".join(parts)


def book_regen_user(prev: str, banned: list[str]) -> str:
    return (
        f"Câu đáp vừa rồi: {prev}\n"
        f"Câu này dùng {len(banned)} từ NGOÀI vốn từ của người học: {', '.join(banned)} (quá {MAX_NEW_WORDS} từ cho phép).\n"
        f"Viết lại câu đáp cùng ý, dùng tối đa {MAX_NEW_WORDS} từ ngoài DANH SÁCH TỪ ĐƯỢC PHÉP và giải thích chúng. Trả JSON: "
        '{"reply": {"hanzi": "...", "vi": "..."' + NEW_WORDS_FIELD + '}}'
    )


EXPLAIN_SYSTEM = TEACHER + " Nhiệm vụ: giải nghĩa từ mới cho người học sơ cấp."


def explain_words_user(items: list[dict]) -> str:
    lines = "\n".join(f"- {x['hanzi']} (trong câu: {x.get('sentence', '')})" for x in items)
    return (
        "Giải nghĩa các từ sau theo đúng nghĩa trong câu:\n" + lines + "\n"
        'Trả JSON: {"words": [{"hanzi": "...", "pinyin": "có dấu", "meaning_vi": "nghĩa ngắn", '
        '"explain_vi": "1 câu giải thích cách dùng"}]}'
    )


def convo_regen_user(prev: str, banned: list[str]) -> str:
    return (
        f"Câu đáp vừa rồi: {prev}\n"
        f"Câu này dùng các từ NGOÀI vốn từ của người học: {', '.join(banned)}.\n"
        "Viết lại câu đáp cùng ý, CHỈ dùng từ trong DANH SÁCH TỪ ĐƯỢC PHÉP. Trả JSON: "
        '{"reply": {"hanzi": "...", "vi": "..."}}'
    )


# ---------------------------------------------------------------- ôn câu sai

JUDGE_SYSTEM = TEACHER + " Nhiệm vụ: chấm câu viết lại của người học."


def judge_user(original: str, corrected: str, explanation: str, answer: str) -> str:
    return (
        f"Câu sai trước đây: {original}\nCâu đúng tham khảo: {corrected}\nLỗi: {explanation}\n"
        f"Người học viết lại: {answer}\n"
        "Câu viết lại có đúng ngữ pháp, đã sửa được lỗi và giữ ý không? (không cần giống hệt câu tham khảo)\n"
        'Trả JSON: {"correct": true/false, "feedback_vi": "1–2 câu nhận xét"}'
    )


# ---------------------------------------------------------------- báo cáo

REPORT_SYSTEM = TEACHER + """
Nhiệm vụ: viết báo cáo cuối buổi học cho người học, dựa trên dữ liệu thật của buổi (không bịa).
Trả JSON:
{"summary_vi": "2–3 câu tổng quan",
 "strengths": ["điểm mạnh cụ thể cần phát huy", ...],        // 2–4 ý, dẫn chứng từ/câu cụ thể
 "weaknesses": ["điểm yếu cụ thể", ...],                       // 2–4 ý
 "grammar_notes": [{"point": "điểm ngữ pháp bị sai", "explanation_vi": "giải thích & cách nhớ",
                    "examples": ["câu đúng mẫu 1", "câu đúng mẫu 2"]}],
 "next_steps": ["việc nên làm ở buổi sau", ...]}"""


def report_user(data: dict) -> str:
    return "Dữ liệu buổi học (JSON):\n" + json.dumps(data, ensure_ascii=False)[:20000]
