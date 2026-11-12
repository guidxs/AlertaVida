"""Create a visual review sheet from YOLO-processed candidate videos."""

import argparse
import csv
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[2]
METRICS_PATH = PROJECT_DIR / "videos" / "candidates_output" / "metrics.json"
PROCESSED_DIR = PROJECT_DIR / "videos" / "candidates_output"
ORIGINAL_DIR = PROJECT_DIR / "videos" / "candidates"
REVIEW_DIR = PROJECT_DIR / "videos" / "review"
SUPPORTED_VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm"}
THUMBNAIL_SIZE = (320, 180)
LABEL_HEIGHT = 34
VIDEO_COLUMN_LABELS = (
    "Original -1s",
    "YOLO -1s",
    "Original acidente",
    "YOLO acidente",
    "Original +1s",
    "YOLO +1s",
)


def parse_time(value: Any) -> float | None:
    """Parse accident_time as seconds or as MM:SS / HH:MM:SS."""
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        if ":" not in text:
            return float(text)
        parts = [float(part) for part in text.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        return None
    return None


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def find_metadata_path(requested: Path | None) -> Path | None:
    if requested is not None:
        resolved = requested if requested.is_absolute() else PROJECT_DIR / requested
        return resolved.resolve() if resolved.is_file() else None
    candidates = (
        PROJECT_DIR / "metadata-real.csv",
        PROJECT_DIR / "dataset" / "metadata-real.csv",
        PROJECT_DIR.parent / "metadata-real.csv",
    )
    return next((path for path in candidates if path.is_file()), None)


def parse_accident_times(handle: io.StringIO) -> dict[str, float]:
    """Parse metadata CSV text into a video-stem to accident-time mapping."""
    sample = handle.read(8192)
    handle.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(handle, dialect=dialect))

    if not rows:
        raise ValueError("CSV de metadados sem linhas de dados.")

    time_column = next(
        (key for key in rows[0] if normalized_key(key or "") == "accidenttime"),
        None,
    )
    if time_column is None:
        raise ValueError("Coluna accident_time não encontrada no CSV de metadados.")

    preferred_video_columns = {
        "video", "videoname", "videofile", "filename", "filepath", "file", "name"
    }
    video_columns = [
        key
        for key in rows[0]
        if normalized_key(key or "") in preferred_video_columns
    ]
    mapping: dict[str, float] = {}
    for row in rows:
        accident_time = parse_time(row.get(time_column))
        if accident_time is None:
            continue
        candidates = [row.get(column, "") for column in video_columns]
        # Accommodate metadata schemas with a differently named video column.
        candidates.extend(
            value
            for key, value in row.items()
            if key != time_column and value and str(value).lower().endswith(tuple(SUPPORTED_VIDEO_EXTENSIONS))
        )
        for candidate in candidates:
            candidate_text = str(candidate or "").strip().replace("\\", "/")
            if candidate_text:
                mapping[Path(candidate_text).stem.lower()] = accident_time
    return mapping


def load_accident_times(csv_path: Path) -> dict[str, float]:
    """Read an extracted metadata-real.csv file."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return parse_accident_times(io.StringIO(handle.read()))


def load_accident_times_from_zip(zip_path: Path) -> dict[str, float]:
    """Read metadata-real.csv directly from the ZIP without extracting it."""
    entry_name = "metadata-real.csv"
    with zipfile.ZipFile(zip_path, "r") as archive:
        try:
            csv_bytes = archive.read(entry_name)
        except KeyError as error:
            raise FileNotFoundError(
                f"Entrada {entry_name} não encontrada em {zip_path}"
            ) from error
    csv_text = csv_bytes.decode("utf-8-sig")
    return parse_accident_times(io.StringIO(csv_text, newline=""))


def find_video(directory: Path, stem: str) -> Path | None:
    if not directory.is_dir():
        return None
    for path in directory.iterdir():
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
            and path.stem.lower() == stem.lower()
        ):
            return path
    return None


def read_frame_at(path: Path, seconds: float) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return None
        capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, seconds) * 1000)
        success, frame = capture.read()
        if not success or frame is None:
            return None
        return cv2.resize(frame, THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA)
    finally:
        capture.release()


def make_placeholder(message: str) -> np.ndarray:
    image = np.full((THUMBNAIL_SIZE[1], THUMBNAIL_SIZE[0], 3), 35, dtype=np.uint8)
    cv2.putText(
        image,
        message,
        (14, THUMBNAIL_SIZE[1] // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (185, 185, 185),
        1,
        cv2.LINE_AA,
    )
    return image


def make_labeled_cell(frame: np.ndarray | None, label: str, missing: str) -> np.ndarray:
    image = frame.copy() if frame is not None else make_placeholder(missing)
    band = np.full((LABEL_HEIGHT, THUMBNAIL_SIZE[0], 3), 22, dtype=np.uint8)
    cv2.putText(
        band,
        label,
        (9, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        (235, 240, 245),
        1,
        cv2.LINE_AA,
    )
    return np.vstack((band, image))


def create_sheet(metrics: list[dict[str, Any]], accident_times: dict[str, float]) -> tuple[np.ndarray, list[str]]:
    rows: list[np.ndarray] = []
    warnings: list[str] = []
    header_height = 44
    grid_width = THUMBNAIL_SIZE[0] * len(VIDEO_COLUMN_LABELS)
    header = np.full((header_height, grid_width, 3), 17, dtype=np.uint8)
    for column, label in enumerate(VIDEO_COLUMN_LABELS):
        x = column * THUMBNAIL_SIZE[0] + 10
        cv2.putText(header, label, (x, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (95, 190, 245), 1, cv2.LINE_AA)
    rows.append(header)

    for index, item in enumerate(metrics, start=1):
        video_name = str(item.get("nome", "")).strip()
        stem = Path(video_name).stem
        accident_time = accident_times.get(stem.lower())
        processed_path = find_video(PROCESSED_DIR, stem)
        original_path = find_video(ORIGINAL_DIR, stem)
        missing: list[str] = []
        if accident_time is None:
            warnings.append(f"Sem accident_time no CSV para {video_name}.")
            continue
        if processed_path is None:
            warnings.append(f"Vídeo processado não encontrado para {video_name} em {PROCESSED_DIR}.")
        if original_path is None:
            warnings.append(f"Vídeo original não encontrado para {video_name} em {ORIGINAL_DIR}.")

        cells: list[np.ndarray] = []
        for offset, moment_name in ((-1, "-1s"), (0, "acidente"), (1, "+1s")):
            target_time = max(0.0, accident_time + offset)
            timestamp_label = f"{target_time:.2f}s"
            source_frame = read_frame_at(original_path, target_time) if original_path else None
            processed_frame = read_frame_at(processed_path, target_time) if processed_path else None
            if original_path and source_frame is None:
                warnings.append(f"Não foi possível ler frame original: {original_path.name} em {timestamp_label}.")
            if processed_path and processed_frame is None:
                warnings.append(f"Não foi possível ler frame processado: {processed_path.name} em {timestamp_label}.")
            cells.append(make_labeled_cell(source_frame, f"{moment_name} | {timestamp_label}", "Original indisponível"))
            cells.append(make_labeled_cell(processed_frame, f"{moment_name} | {timestamp_label}", "Processado indisponível"))

        row_image = np.hstack(cells)
        row_header = np.full((34, grid_width, 3), 28, dtype=np.uint8)
        cv2.putText(
            row_header,
            f"{index:02d}. {video_name}  |  accident_time: {accident_time:.2f}s",
            (12, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
        rows.extend((row_header, row_image))
        print(f"[{index}/{len(metrics)}] Frames capturados: {video_name}")

    if len(rows) == 1:
        raise ValueError("Nenhuma linha pôde ser montada. Confira nomes de vídeos e accident_time no CSV.")
    return np.vstack(rows), warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Caminho de um metadata-real.csv extraído. Se omitido, usa o ZIP.",
    )
    parser.add_argument(
        "--metadata-zip",
        type=Path,
        default=PROJECT_DIR / "videos" / "archive.zip",
        help="ZIP que contém metadata-real.csv (padrão: videos/archive.zip).",
    )
    args = parser.parse_args()
    metadata_zip = args.metadata_zip
    if not metadata_zip.is_absolute():
        metadata_zip = PROJECT_DIR / metadata_zip
    metadata_zip = metadata_zip.resolve()

    if not METRICS_PATH.is_file():
        raise FileNotFoundError(f"Métricas não encontradas: {METRICS_PATH}")
    if args.metadata is not None:
        metadata_path = find_metadata_path(args.metadata)
        if metadata_path is None:
            raise FileNotFoundError(f"CSV de metadados não encontrado: {args.metadata}")
        accident_times = load_accident_times(metadata_path)
        metadata_source = metadata_path
    else:
        if not metadata_zip.is_file():
            raise FileNotFoundError(f"ZIP de metadados não encontrado: {metadata_zip}")
        accident_times = load_accident_times_from_zip(metadata_zip)
        metadata_source = metadata_zip

    with METRICS_PATH.open("r", encoding="utf-8") as handle:
        metrics_data = json.load(handle)
    metrics = metrics_data.get("videos", [])
    if not metrics:
        raise ValueError(f"Nenhum vídeo listado em {METRICS_PATH}")
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheet, warnings = create_sheet(metrics, accident_times)
    output_path = REVIEW_DIR / f"review_sheet_{datetime.now():%Y%m%d_%H%M%S}.jpg"
    if not cv2.imwrite(str(output_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise OSError(f"Não foi possível salvar a imagem: {output_path}")

    print(f"\nContact sheet salva em: {output_path}")
    print(f"Metadados utilizados: {metadata_source} (metadata-real.csv)")
    if warnings:
        print("\nAvisos:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("Todos os frames originais e processados solicitados foram encontrados e lidos.")


if __name__ == "__main__":
    main()
