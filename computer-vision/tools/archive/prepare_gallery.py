"""Prepare the approved batch 2 videos and a metadata manifest for the gallery."""

import csv
import io
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[2]
ORIGINAL_DIR = PROJECT_DIR / "videos" / "candidates_batch2"
PROCESSED_DIR = PROJECT_DIR / "videos" / "candidates_batch2_output"
METRICS_PATH = PROCESSED_DIR / "metrics.json"
METADATA_ZIP = PROJECT_DIR / "videos" / "archive.zip"
GALLERY_DIR = PROJECT_DIR / "videos" / "gallery"
METADATA_ENTRY = "metadata-real.csv"

APPROVED_VIDEOS = {
    "y4Evv5By6sg_1_00": "Boa detecção do acidente.",
    "y4Evv5By6sg_4_00": "Boa detecção do acidente.",
    "TXZfPbiopOE_00": "Boa detecção do acidente.",
    "russia16_00": "Detecta antes (0.60) e durante a colisão (0.65).",
    "OehnhIPFm4Q_04": "Detecta a derrapagem e depois a colisão.",
    "N6zJ2inqJn0_0_00": "Falso positivo antes (0.78), mas detecta a colisão (0.80).",
    "L334aqEJxys_0_00": "Boa detecção do acidente.",
}
VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm"}


def read_metadata() -> dict[str, dict[str, Any]]:
    """Read dataset metadata directly from archive.zip, without extracting it."""
    with zipfile.ZipFile(METADATA_ZIP, "r") as archive:
        try:
            csv_data = archive.read(METADATA_ENTRY)
        except KeyError as error:
            raise FileNotFoundError(
                f"{METADATA_ENTRY} não encontrado em {METADATA_ZIP}"
            ) from error

    text = csv_data.decode("utf-8-sig")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    required = {"path", "type", "duration", "accident_time", "width", "height"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"Colunas esperadas ausentes em {METADATA_ENTRY}: {required}")

    return {
        Path((row.get("path") or "").replace("\\", "/")).stem: row
        for row in reader
        if row.get("path")
    }


def find_video(directory: Path, stem: str) -> Path:
    if not directory.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {directory}")
    matches = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
        and path.stem.lower() == stem.lower()
    ]
    if not matches:
        raise FileNotFoundError(f"Vídeo {stem} não encontrado em {directory}")
    if len(matches) > 1:
        raise RuntimeError(f"Mais de uma extensão encontrada para {stem} em {directory}: {matches}")
    return matches[0]


def copy_without_overwriting(source: Path, desired_path: Path) -> Path:
    """Copy a file, reusing identical output or selecting a free suffix."""
    destination = desired_path
    counter = 1
    while destination.exists():
        if destination.is_file() and destination.stat().st_size == source.stat().st_size and destination.read_bytes() == source.read_bytes():
            # Reuse only an identical file; never rewrite an existing artifact.
            return destination
        destination = desired_path.with_name(
            f"{desired_path.stem}_{counter}{desired_path.suffix}"
        )
        counter += 1
    shutil.copy2(source, destination)
    return destination


def transcode_to_h264_mp4(source: Path, desired_path: Path, ffmpeg: str) -> Path:
    """Encode H.264 MP4 to a temporary file and publish only successful output."""
    destination = desired_path
    counter = 1
    while destination.exists():
        # Never trust or overwrite an existing artifact; publish to a free name.
        destination = desired_path.with_name(f"{desired_path.stem}_{counter}.mp4")
        counter += 1

    with tempfile.NamedTemporaryFile(
        prefix=f".{source.stem}_", suffix=".partial", dir=desired_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        command = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            str(temporary_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            details = completed.stderr.strip() or f"código de saída {completed.returncode}"
            raise RuntimeError(details)
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise RuntimeError("FFmpeg retornou sucesso, mas não gerou arquivo de saída válido.")
        # FFmpeg was explicitly instructed to encode libx264 into an MP4 container.
        temporary_path.replace(destination)
        return destination
    except (OSError, RuntimeError) as error:
        raise RuntimeError(f"Falha ao converter {source.name} para MP4/H.264: {error}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def build_gallery() -> list[dict[str, Any]]:
    for required_path in (METRICS_PATH, METADATA_ZIP):
        if not required_path.is_file():
            raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {required_path}")

    metrics_data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    metrics_by_stem = {
        Path(item["nome"]).stem.lower(): item for item in metrics_data.get("videos", [])
    }
    metadata_by_stem = {stem.lower(): row for stem, row in read_metadata().items()}
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
        ffmpeg_issue = None
    except (ImportError, RuntimeError) as error:
        ffmpeg = None
        ffmpeg_issue = (
            "Não foi possível localizar o FFmpeg fornecido por imageio-ffmpeg: "
            f"{error}"
        )

    originals_dir = GALLERY_DIR / "originals"
    processed_dir = GALLERY_DIR / "processed"
    originals_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for stem, note in APPROVED_VIDEOS.items():
        key = stem.lower()
        original_source = find_video(ORIGINAL_DIR, stem)
        processed_source = find_video(PROCESSED_DIR, stem)
        metadata = metadata_by_stem.get(key)
        metrics = metrics_by_stem.get(key)
        if metadata is None:
            raise KeyError(f"Metadados não encontrados para {stem}")
        if metrics is None:
            raise KeyError(f"Métricas não encontradas para {stem}")

        original_destination = copy_without_overwriting(
            original_source, originals_dir / original_source.name
        )
        conversion_issue = None
        if ffmpeg:
            try:
                processed_destination = transcode_to_h264_mp4(
                    processed_source,
                    processed_dir / f"{stem}.mp4",
                    ffmpeg,
                )
                browser_compatible = True
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                processed_destination = copy_without_overwriting(
                    processed_source, processed_dir / processed_source.name
                )
                browser_compatible = False
                conversion_issue = str(error)
        else:
            processed_destination = copy_without_overwriting(
                processed_source, processed_dir / processed_source.name
            )
            browser_compatible = False
            conversion_issue = ffmpeg_issue

        row = {
            "name": stem,
            "accident_type": metadata["type"],
            "duration_seconds": float(metadata["duration"]),
            "accident_time_seconds": float(metadata["accident_time"]),
            "resolution": {
                "width": int(metadata["width"]),
                "height": int(metadata["height"]),
            },
            "max_confidence": metrics.get("maior_confianca"),
            "detected_frames_percentage": metrics.get(
                "percentual_quadros_com_deteccao"
            ),
            "detected_frames": metrics.get("quadros_com_deteccao"),
            "total_frames": metrics.get("quantidade_quadros"),
            "original_video": original_destination.relative_to(GALLERY_DIR).as_posix(),
            "processed_video": processed_destination.relative_to(GALLERY_DIR).as_posix(),
            "processed_video_mime_type": (
                "video/mp4" if browser_compatible else "video/x-msvideo"
            ),
            "browser_compatible": browser_compatible,
            "observation": note,
        }
        if conversion_issue:
            row["processing_issue"] = conversion_issue
        entries.append(row)

    return entries


def main() -> None:
    manifest_path = GALLERY_DIR / "gallery.json"
    entries = build_gallery()
    all_compatible = all(item["browser_compatible"] for item in entries)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_count": len(entries),
        "processed_video_format": (
            "H.264 MP4" if all_compatible else "Mixed; failed conversions retain original AVI"
        ),
        "videos": entries,
    }
    # Replace the manifest only after conversion results for every video are known.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=GALLERY_DIR,
        prefix=".gallery_", suffix=".tmp", delete=False,
    ) as handle:
        manifest_temp = Path(handle.name)
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    manifest_temp.replace(manifest_path)

    total_bytes = sum(
        path.stat().st_size for path in GALLERY_DIR.rglob("*") if path.is_file()
    )
    print(f"Galeria preparada: {GALLERY_DIR}")
    print(f"Manifesto: {manifest_path}")
    print(f"Vídeos listados: {len(entries)}")
    print(f"Tamanho total da galeria: {total_bytes / (1024 * 1024):.2f} MiB ({total_bytes} bytes)")
    if not all(item["browser_compatible"] for item in entries):
        print("AVISO: algumas versões processadas não foram convertidas para MP4 H.264.")
        for item in entries:
            if not item["browser_compatible"]:
                print(f"- {item['name']}: {item.get('processing_issue', 'formato não validado')}")


if __name__ == "__main__":
    main()
