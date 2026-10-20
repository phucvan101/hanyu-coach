import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

DATA_DIR = Path(os.environ.get("HANYU_DATA_DIR", PROJECT_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "hanyu.sqlite"
TTS_CACHE_DIR = DATA_DIR / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IME_DB_PATH = APP_DIR / "data" / "ime.sqlite"

STATIC_DIR = Path(os.environ.get("HANYU_STATIC_DIR", PROJECT_DIR / "frontend" / "dist"))

# Learning rules
PASS_THRESHOLD = 70          # % để mở khoá bước tiếp theo
QUIZ_MAX_QUESTIONS = 20
REVIEW_MAX_WORDS = 6
REVIEW_MAX_SENTENCES = 3
CONVO_TURNS_CONTROLLED = 8   # số lượt người học trong hội thoại có kiểm soát
CONVO_TURNS_FREE = 8

FAKE_LLM = os.environ.get("HANYU_FAKE_LLM") == "1"
