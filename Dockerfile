# Hanyu Coach — ứng dụng luyện tiếng Trung chạy trên máy cá nhân
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HANYU_DATA_DIR=/app/data \
    HANYU_STATIC_DIR=/app/frontend/dist \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements.txt \
    && python -c "import jieba; jieba.initialize()"

COPY backend/ /app/backend/
COPY frontend/dist/ /app/frontend/dist/

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
