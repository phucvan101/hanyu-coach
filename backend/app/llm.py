"""Gọi LLM: Gemini (API gốc) + một nhà cung cấp tương thích OpenAI (mặc định GLM của Zhipu).

- Thử lần lượt theo thứ tự trong cài đặt; máy chủ bận (429/5xx/timeout) -> chờ thử lại 1 lần rồi chuyển nhà cung cấp kế tiếp.
- Cuối cùng thử các model Gemini dự phòng (hạn mức & máy chủ riêng).
- Mọi lời gọi đều yêu cầu trả JSON và được parse chịu lỗi.
- Nhận dạng giọng nói (STT) chỉ Gemini làm được (nhận audio WAV) -> dự phòng bằng các model Gemini khác.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time

import httpx

from . import fake_llm
from .config import FAKE_LLM
from .db import get_db, get_setting

log = logging.getLogger("hanyu.llm")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

DEFAULTS = {
    "llm_order": "gemini,openai",
    "gemini_model": "gemini-2.5-flash",
    "openai_label": "GLM (Zhipu)",
    "openai_base_url": "https://open.bigmodel.cn/api/paas/v4",
    "openai_model": "glm-4.7-flash",
}


class LLMError(Exception):
    pass


def load_settings() -> dict:
    with get_db() as db:
        s = {k: get_setting(db, k, v) for k, v in DEFAULTS.items()}
        s["gemini_api_key"] = get_setting(db, "gemini_api_key", "") or ""
        s["openai_api_key"] = get_setting(db, "openai_api_key", "") or ""
    return s


def configured_providers(s: dict | None = None) -> list[str]:
    s = s or load_settings()
    out = []
    for name in [x.strip() for x in s["llm_order"].split(",") if x.strip()]:
        if name == "gemini" and s["gemini_api_key"]:
            out.append("gemini")
        elif name == "openai" and s["openai_api_key"] and s["openai_base_url"]:
            out.append("openai")
    return out


def is_configured() -> bool:
    return FAKE_LLM or bool(configured_providers())


def parse_json(text: str):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise LLMError("Model trả về dữ liệu không đúng định dạng JSON")


class _Retryable(Exception):
    pass


class _Busy(_Retryable):
    """Hết hạn mức tạm thời / máy chủ quá tải / mất kết nối: thường hết sau vài giây."""


class _ModelNotFound(_Retryable):
    pass


def _pick_flash(names: list[str]) -> str | None:
    def ver(n):
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0

    bad = ("lite", "image", "tts", "live", "audio", "exp", "embedding", "thinking", "native")
    good = [n for n in names if "flash" in n and not any(b in n for b in bad)]
    stable = [n for n in good if "preview" not in n] or good
    return max(stable, key=ver) if stable else None


def _auto_fix_gemini_model(s: dict) -> bool:
    """Model Gemini không còn tồn tại -> tự chọn bản flash mới nhất và lưu lại."""
    try:
        names = list_gemini_models()
    except Exception:  # noqa: BLE001
        return False
    new = _pick_flash(names)
    if not new or new == s["gemini_model"]:
        return False
    from .db import set_setting

    with get_db() as db:
        set_setting(db, "gemini_model", new)
    log.warning("Gemini model %s không khả dụng, chuyển sang %s", s["gemini_model"], new)
    s["gemini_model"] = new
    return True


def _gemini_generate(s: dict, parts: list, system: str | None, temperature: float, json_mode: bool, timeout: float) -> str:
    body: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"{GEMINI_BASE}/models/{s['gemini_model']}:generateContent"
    try:
        r = httpx.post(url, json=body, headers={"x-goog-api-key": s["gemini_api_key"]}, timeout=timeout)
    except httpx.HTTPError as e:
        raise _Busy(f"Gemini {s['gemini_model']}: lỗi kết nối ({e.__class__.__name__})")
    if r.status_code == 429 or r.status_code >= 500:
        raise _Busy(f"Gemini {s['gemini_model']}: HTTP {r.status_code} (hết hạn mức hoặc máy chủ bận)")
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            msg = r.text[:200]
        if r.status_code == 404 or "not found" in msg.lower() or "no longer available" in msg.lower():
            raise _ModelNotFound(f"Gemini: model {s['gemini_model']} không khả dụng – {msg}")
        raise _Retryable(f"Gemini: HTTP {r.status_code} – {msg}")
    data = r.json()
    cands = data.get("candidates") or []
    if not cands:
        raise _Retryable(f"Gemini: không có kết quả ({data.get('promptFeedback', {})})")
    out = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought"))
    if not out.strip():
        raise _Retryable("Gemini: kết quả rỗng")
    return out


def _openai_generate(s: dict, system: str | None, user: str, temperature: float, json_mode: bool, timeout: float) -> str:
    base = s["openai_base_url"].rstrip("/")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    body: dict = {"model": s["openai_model"], "messages": messages, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if "bigmodel.cn" in base or "z.ai" in base:
        body["thinking"] = {"type": "disabled"}
    headers = {"Authorization": f"Bearer {s['openai_api_key']}"}
    for attempt in range(2):
        try:
            r = httpx.post(f"{base}/chat/completions", json=body, headers=headers, timeout=timeout)
        except httpx.HTTPError as e:
            raise _Busy(f"{s['openai_label']}: lỗi kết nối ({e.__class__.__name__})")
        if r.status_code == 400 and attempt == 0 and ("response_format" in body or "thinking" in body):
            body.pop("response_format", None)
            body.pop("thinking", None)
            continue
        break
    if r.status_code == 429 or r.status_code >= 500:
        raise _Busy(f"{s['openai_label']}: HTTP {r.status_code} (hết hạn mức hoặc máy chủ bận)")
    if r.status_code >= 400:
        raise _Retryable(f"{s['openai_label']}: HTTP {r.status_code} – {r.text[:200]}")
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        raise _Retryable(f"{s['openai_label']}: kết quả không hợp lệ")


# model Gemini thử thêm khi các nhà cung cấp chính đều lỗi: mỗi model có hạn mức & máy chủ riêng
GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-flash-lite-latest"]
BUSY_RETRY_DELAY = 1.5


def _label(prov: str, s: dict) -> str:
    return f"gemini/{s['gemini_model']}" if prov == "gemini" else prov


def _gemini_fallbacks(s: dict) -> list[dict]:
    return [{**s, "gemini_model": m} for m in GEMINI_FALLBACK_MODELS if m != s["gemini_model"]]


def _attempt_plan(s: dict, providers: list[str]) -> list[tuple[str, dict, bool]]:
    """(nhà cung cấp, cài đặt, là lựa chọn chính?) theo thứ tự thử."""
    plan = [(p, s, True) for p in providers]
    if "gemini" in providers:
        plan += [("gemini", fs, False) for fs in _gemini_fallbacks(s)]
    return plan


def chat_json(task: str, system: str, user: str, temperature: float = 0.6, timeout: float = 90) -> dict:
    """Gọi LLM, trả về dict. `task` dùng cho log và chế độ giả lập khi test."""
    if FAKE_LLM:
        return fake_llm.respond(task, system, user)
    s = load_settings()
    providers = configured_providers(s)
    if not providers:
        raise LLMError("Chưa cấu hình API key. Vào Cài đặt để nhập Gemini API key.")
    errors = []
    for prov, ss, primary in _attempt_plan(s, providers):
        for attempt in range(2):
            t0 = time.time()
            try:
                if prov == "gemini":
                    text = _gemini_generate(ss, [{"text": user}], system, temperature, True, timeout)
                else:
                    text = _openai_generate(ss, system, user, temperature, True, timeout)
                data = parse_json(text)
                log.info("LLM %s via %s ok in %.1fs", task, _label(prov, ss), time.time() - t0)
                return data
            except _ModelNotFound as e:
                errors.append(str(e))
                if attempt == 0 and primary and prov == "gemini" and _auto_fix_gemini_model(ss):
                    continue
                break
            except _Busy as e:
                errors.append(str(e))
                log.warning("LLM %s via %s busy: %s", task, _label(prov, ss), e)
                if attempt == 0 and primary:
                    time.sleep(BUSY_RETRY_DELAY)
                    continue
                break
            except _Retryable as e:
                errors.append(str(e))
                log.warning("LLM %s via %s failed: %s", task, _label(prov, ss), e)
                break  # chuyển sang nhà cung cấp kế tiếp
            except LLMError as e:
                errors.append(f"{prov}: {e}")
                if attempt == 1:
                    break
    raise LLMError("Không gọi được AI (đã thử cả AI dự phòng). " + " | ".join(dict.fromkeys(errors)))


def transcribe(wav_bytes: bytes) -> str:
    if FAKE_LLM:
        return "我想吃饺子"
    s = load_settings()
    if not s["gemini_api_key"]:
        raise LLMError("Nhận dạng giọng nói cần Gemini API key.")
    parts = [
        {"text": (
            "Chép lại chính xác lời nói tiếng Phổ thông (Mandarin) trong đoạn audio bằng chữ Hán giản thể. "
            "KHÔNG sửa lỗi ngữ pháp, KHÔNG thêm chữ. Nếu người nói dùng tiếng Việt thì chép tiếng Việt. "
            'Trả JSON: {"text": "..."}. Nếu không nghe rõ trả {"text": ""}.'
        )},
        {"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(wav_bytes).decode()}},
    ]
    errors = []
    for ss, primary in [(s, True)] + [(fs, False) for fs in _gemini_fallbacks(s)]:
        for attempt in range(2):
            try:
                text = _gemini_generate(ss, parts, None, 0.0, True, 60)
                if not primary:
                    log.info("STT via dự phòng gemini/%s ok", ss["gemini_model"])
                return (parse_json(text).get("text") or "").strip()
            except _ModelNotFound as e:
                errors.append(str(e))
                if attempt == 0 and primary and _auto_fix_gemini_model(ss):
                    continue
                break
            except _Busy as e:
                errors.append(str(e))
                log.warning("STT via gemini/%s busy: %s", ss["gemini_model"], e)
                if attempt == 0 and primary:
                    time.sleep(BUSY_RETRY_DELAY)
                    continue
                break
            except _Retryable as e:
                errors.append(str(e))
                break
    raise LLMError("Nhận dạng giọng nói lỗi (chỉ Gemini nghe được audio, đã thử cả model dự phòng): "
                   + " | ".join(dict.fromkeys(errors)))


def test_provider(name: str) -> dict:
    s = load_settings()
    t0 = time.time()
    try:
        if name == "gemini":
            if not s["gemini_api_key"]:
                return {"ok": False, "message": "Chưa nhập Gemini API key"}
            prompt = [{"text": '用中文说"你好"，只返回JSON {"reply": "..."}'}]
            try:
                text = _gemini_generate(s, prompt, None, 0.2, True, 30)
            except _ModelNotFound:
                if not _auto_fix_gemini_model(s):
                    raise
                text = _gemini_generate(s, prompt, None, 0.2, True, 30)
        else:
            if not s["openai_api_key"]:
                return {"ok": False, "message": "Chưa nhập API key"}
            text = _openai_generate(s, None, '用中文说"你好"，只返回JSON {"reply": "..."}', 0.2, True, 30)
        reply = parse_json(text).get("reply", "")
        model = s["gemini_model"] if name == "gemini" else s["openai_model"]
        return {"ok": True, "message": f"Kết nối tốt – {model} ({time.time() - t0:.1f}s): {reply}"}
    except (_Retryable, LLMError) as e:
        return {"ok": False, "message": str(e)}


def list_gemini_models() -> list[str]:
    s = load_settings()
    if not s["gemini_api_key"]:
        raise LLMError("Chưa nhập Gemini API key")
    r = httpx.get(f"{GEMINI_BASE}/models", headers={"x-goog-api-key": s["gemini_api_key"]}, params={"pageSize": 200}, timeout=20)
    if r.status_code >= 400:
        raise LLMError(f"HTTP {r.status_code}: {r.text[:200]}")
    names = []
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            n = m["name"].split("/", 1)[-1]
            if "flash" in n or "pro" in n:
                names.append(n)
    return sorted(set(names))
