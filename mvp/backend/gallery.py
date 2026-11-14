"""Read-only API for the approved video demonstration gallery."""

import json
import re
from pathlib import Path, PurePosixPath
from typing import Iterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse


GALLERY_ROOT = (
    Path(__file__).resolve().parents[2]
    / "computer-vision"
    / "videos"
    / "gallery"
).resolve()
MANIFEST_PATH = GALLERY_ROOT / "gallery.json"
router = APIRouter(prefix="/api/gallery", tags=["gallery"])


def load_manifest() -> dict:
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Manifesto da galeria indisponível.") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("videos"), list):
        raise HTTPException(status_code=503, detail="Manifesto da galeria inválido.")
    return manifest


def resolve_approved_video(relative_path: str, manifest: dict) -> Path:
    """Resolve only MP4 paths explicitly published by gallery.json."""
    approved_paths: set[str] = set()
    for video in manifest["videos"]:
        if not isinstance(video, dict):
            continue
        original_path = video.get("original_video")
        if isinstance(original_path, str):
            approved_paths.add(original_path)
        processed_path = video.get("processed_video")
        if isinstance(processed_path, str) and video.get("browser_compatible") is True:
            approved_paths.add(processed_path)

    if relative_path not in approved_paths:
        raise HTTPException(status_code=404, detail="Vídeo não publicado na galeria.")

    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".mp4":
        raise HTTPException(status_code=404, detail="Caminho de vídeo inválido.")

    candidate = (GALLERY_ROOT / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(GALLERY_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Caminho de vídeo inválido.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado.")
    return candidate


def parse_byte_range(range_header: str, file_size: int) -> tuple[int, int]:
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not match or file_size <= 0:
        raise ValueError("Invalid byte range")
    first, last = match.groups()
    if not first and not last:
        raise ValueError("Invalid byte range")
    if not first:
        suffix_length = int(last)
        if suffix_length <= 0:
            raise ValueError("Invalid byte range")
        start = max(file_size - suffix_length, 0)
        return start, file_size - 1
    start = int(first)
    end = min(int(last), file_size - 1) if last else file_size - 1
    if start >= file_size or end < start:
        raise ValueError("Unsatisfiable byte range")
    return start, end


def stream_file(path: Path, start: int, length: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as handle:
        handle.seek(start)
        remaining = length
        while remaining:
            chunk = handle.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("")
def gallery_manifest() -> dict:
    return load_manifest()


@router.get("/videos")
def gallery_video(request: Request, path: str = Query(..., min_length=1)) -> Response:
    manifest = load_manifest()
    video_path = resolve_approved_video(path, manifest)
    file_size = video_path.stat().st_size
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"}
    range_header = request.headers.get("range")

    if range_header:
        try:
            start, end = parse_byte_range(range_header, file_size)
        except ValueError as exc:
            return Response(
                status_code=416,
                headers={**headers, "Content-Range": f"bytes */{file_size}"},
            )
        return StreamingResponse(
            stream_file(video_path, start, end - start + 1),
            status_code=206,
            media_type="video/mp4",
            headers={
                **headers,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(end - start + 1),
            },
        )

    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers=headers,
    )
