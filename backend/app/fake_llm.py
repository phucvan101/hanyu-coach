"""LLM giả lập (HANYU_FAKE_LLM=1) – chỉ dùng để test/demo khi chưa có API key."""
from __future__ import annotations

import re

FUNC = set("了吧呢把都也还再才就给对在吗啊")


def respond(task: str, system: str, user: str) -> dict:
    if task == "enrich":
        words = []
        for line in user.splitlines()[1:]:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            h = parts[0]
            words.append({
                "hanzi": h,
                "primary_meaning": parts[2].split(";")[0].strip(),
                "is_function_word": h in FUNC,
                "usage_vi": "trợ từ" if h in FUNC else "",
                "example_zh": f"我有{h}。",
                "example_vi": f"Tôi có {parts[2].split(';')[0].strip()}.",
            })
        return {"words": words}
    if task == "group":
        words = [re.sub(r"\s*\(.*\)$", "", l).strip() for l in user.splitlines()[1:] if l.strip()]
        units = []
        for i in range(0, len(words), 15):
            units.append({
                "title_vi": f"Chủ đề {i // 15 + 1}", "title_zh": f"主题{i // 15 + 1}",
                "scenario_vi": "Bạn gặp một người bạn mới ở trường.",
                "ai_role_vi": "Bạn cùng lớp", "user_role_vi": "Bạn",
                "words": words[i:i + 15],
            })
        return {"units": units}
    if task == "grammar":
        return {"grammar_points": [
            {"pattern": "主语 + 在 + 地点 + 动词", "explanation_vi": "Làm gì ở đâu", "example_zh": "我在学校学习。", "example_vi": "Tôi học ở trường."},
            {"pattern": "动词 + 了", "explanation_vi": "Hành động đã hoàn thành", "example_zh": "我吃了。", "example_vi": "Tôi ăn rồi."},
        ]}
    if task == "convo_open":
        if '"new_words"' in user:
            return {"intro_vi": "Trò chuyện theo chủ đề bạn chọn.",
                    "reply": {"hanzi": "你好！你喜欢喝拿铁吗？", "vi": "Chào bạn! Bạn thích uống latte không?",
                              "new_words": [{"hanzi": "拿铁", "pinyin": "nátiě", "meaning_vi": "cà phê latte", "explain_vi": "danh từ"},
                                            {"hanzi": "喜欢", "pinyin": "xǐhuan", "meaning_vi": "thích", "explain_vi": "khai nhầm"}]}}
        return {"intro_vi": "Bạn đang ở quán ăn, hãy gọi món.", "reply": {"hanzi": "你好！欢迎！你想吃什么？", "vi": "Xin chào! Chào mừng! Bạn muốn ăn gì?"}}
    if task == "convo_turn":
        m = re.search(r"Câu mới của người học: (.*)", user)
        text = (m.group(1).strip() if m else "")
        if re.fullmatch(r"[a-zA-Z0-9\s]+", text):
            text = "我想吃饺子"
        ok = len(text) >= 4 and "很是" not in text
        ev = {
            "score": 90 if ok else 55, "grammar_score": 90 if ok else 50, "is_correct": ok,
            "corrected": text if ok else "我很高兴。", "corrected_vi": "Tôi rất vui.",
            "errors": [] if ok else [{"type": "ngu_phap", "original": text, "correction": "我很高兴",
                                      "grammar_point": "Tính từ làm vị ngữ không dùng 是",
                                      "explanation_vi": "Trước tính từ dùng 很, không dùng 是."}],
            "hint_vi": "Tốt lắm!" if ok else "Trước tính từ dùng 很, không cần 是.",
            "used_words": [w for w in ["饺子", "茶", "米饭"] if w in text],
            "vietnamese_only": False,
        }
        reply = {"hanzi": "好的。你喝茶吗？", "vi": "Được. Bạn uống trà không?"}
        if '"new_words"' in user:
            reply = {"hanzi": "好的。你去超市吗？", "vi": "Được. Bạn đi siêu thị không?"}
        return {"user_hanzi": text, "evaluation": ev, "reply": reply, "should_end": "lượt cuối" in user}
    if task == "explain_words":
        hz = re.findall(r"^- (\S+) \(", user, re.M)
        return {"words": [{"hanzi": h, "pinyin": "", "meaning_vi": f"nghĩa của {h}", "explain_vi": "giải thích"} for h in hz]}
    if task == "convo_regen":
        return {"reply": {"hanzi": "好的。你要什么？", "vi": "Được. Bạn cần gì?"}}
    if task == "judge":
        ok = bool(re.search(r"[一-鿿]", user.split("Người học viết lại:")[-1]))
        return {"correct": ok, "feedback_vi": "Đúng rồi!" if ok else "Chưa đúng."}
    if task == "report":
        return {"summary_vi": "Buổi học tốt.", "strengths": ["Nhớ nghĩa từ tốt"], "weaknesses": ["Thanh điệu"],
                "grammar_notes": [{"point": "很 + tính từ", "explanation_vi": "Không dùng 是 trước tính từ.", "examples": ["我很好。"]}],
                "next_steps": ["Ôn thanh điệu"]}
    return {}
