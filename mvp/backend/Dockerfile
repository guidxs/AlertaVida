FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Upgrade build-time packaging tools, then install only application requirements
# into a separate prefix that can be copied into the runtime image.
COPY mvp/backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel jaraco.context \
    && python -m pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip setuptools wheel jaraco.context

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/mvp

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/computer-vision/videos/gallery

# The prefix contains the installed runtime dependencies, not the builder's pip.
COPY --from=builder /install/ /usr/local/

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
