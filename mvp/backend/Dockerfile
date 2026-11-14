FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/mvp

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/computer-vision/videos/gallery

COPY mvp/backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

COPY --chown=app:app \
    mvp/backend/__init__.py \
    mvp/backend/config.py \
    mvp/backend/databricks.py \
    mvp/backend/gallery.py \
    mvp/backend/main.py \
    mvp/backend/schemas.py \
    ./backend/

USER app:app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
