"""Dự phòng khi AI bận: thử lại, chuyển nhà cung cấp, rồi model Gemini dự phòng."""
import json
import os
import tempfile

os.environ.setdefault("HANYU_DATA_DIR", tempfile.mkdtemp())

import httpx  # noqa: E402
import pytest  # noqa: E402

from app import llm  # noqa: E402


class Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._p = payload or {}
        self.text = json.dumps(self._p)

    def json(self):
        return self._p


def gemini_ok(text):
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(llm, "FAKE_LLM", False)
    monkeypatch.setattr(llm, "BUSY_RETRY_DELAY", 0)
    monkeypatch.setattr(llm, "load_settings", lambda: {
        **llm.DEFAULTS, "gemini_api_key": "k", "openai_api_key": "k2"})
    calls = []

    def install(handler):
        def post(url, **kw):
            calls.append(url)
            return handler(url, kw)
        monkeypatch.setattr(httpx, "post", post)
    return install, calls


def test_chat_falls_back_to_gemini_lite_when_all_busy(env):
    install, calls = env

    def h(url, kw):
        if "flash-lite" in url:
            return gemini_ok('{"ok": 1}')
        return Resp(503) if "googleapis" in url else Resp(429)
    install(h)
    assert llm.chat_json("t", "sys", "u") == {"ok": 1}
    # gemini chính 2 lần (thử lại sau khi chờ), GLM 2 lần, rồi model dự phòng
    assert sum("gemini-2.5-flash:" in c for c in calls) == 2
    assert sum("bigmodel" in c for c in calls) == 2
    assert "gemini-2.5-flash-lite" in calls[-1]


def test_busy_retry_recovers_on_same_provider(env):
    install, calls = env
    seq = [Resp(503), gemini_ok('{"x": 2}')]
    install(lambda url, kw: seq.pop(0))
    assert llm.chat_json("t", "sys", "u") == {"x": 2}
    assert len(calls) == 2


def test_stt_uses_fallback_gemini_model(env):
    install, calls = env
    install(lambda url, kw: gemini_ok('{"text": "你好"}') if "flash-lite-latest" in url else Resp(503))
    assert llm.transcribe(b"\0" * 4000) == "你好"
    assert not any("bigmodel" in c for c in calls), "GLM không nghe được audio"


def test_stt_error_mentions_fallback(env):
    install, _ = env
    install(lambda url, kw: Resp(503))
    with pytest.raises(llm.LLMError, match="dự phòng"):
        llm.transcribe(b"\0" * 4000)
