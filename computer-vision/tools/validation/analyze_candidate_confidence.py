"""Analyze per-frame YOLO confidence around candidate accident times."""

import csv
import io
import json
import os
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
from tqdm import tqdm
from ultralytics import YOLO


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = (
    PROJECT_DIR
    / "runs"
    / "detect"
    / "runs"
    / "alertavida_yolo11n"
    / "weights"
    / "best.pt"
)
_model_path = Path(os.environ.get("ALERTAVIDA_MODEL_PATH", str(DEFAULT_MODEL_PATH))).expanduser()
MODEL_PATH = (_model_path if _model_path.is_absolute() else PROJECT_DIR / _model_path).resolve()
VIDEO_DIR = PROJECT_DIR / "videos" / "candidates"
METADATA_ZIP = PROJECT_DIR / "videos" / "archive.zip"
OUTPUT_DIR = PROJECT_DIR / "videos" / "review" / "confidence_analysis"

VIDEO_NAMES = (
    "e17Wq4Hpqlk_02.mp4",
    "N6zJ2inqJn0_3_00.mp4",
    "q7UutMH5DTM_00.mp4",
    "russia15_00.mp4",
    "KZl-FNCuiGs_00.mp4",
    "QB42gU5X634_00.mp4",
    "russia8_00.mp4",
)
MIN_CONFIDENCE = 0.10
CONFIDENCE_THRESHOLDS = (0.50, 0.60, 0.70, 0.80)
IMAGE_SIZE = 640
DEVICE = 0
METADATA_ENTRY = "metadata-real.csv"


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def read_accident_times(zip_path: Path) -> dict[str, float]:
    """Read accident_time values keyed by video basename, without extraction."""
    with zipfile.ZipFile(zip_path, "r") as archive:
        try:
            csv_bytes = archive.read(METADATA_ENTRY)
        except KeyError as error:
            raise FileNotFoundError(
                f"Entrada {METADATA_ENTRY} não encontrada em {zip_path}"
            ) from error

    csv_text = csv_bytes.decode("utf-8-sig")
    stream = io.StringIO(csv_text, newline="")
    sample = stream.read(8192)
    stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(stream, dialect=dialect)
    if not reader.fieldnames:
        raise ValueError(f"CSV sem cabeçalho: {METADATA_ENTRY}")

    columns = {normalized_key(column): column for column in reader.fieldnames if column}
    path_column = columns.get("path") or columns.get("filename") or columns.get("video")
    time_column = columns.get("accidenttime")
    if not path_column or not time_column:
        raise ValueError(
            f"O CSV precisa conter path e accident_time; colunas: {reader.fieldnames}"
        )

    accident_times: dict[str, float] = {}
    for row in reader:
        path_value = (row.get(path_column) or "").strip().replace("\\", "/")
        time_value = (row.get(time_column) or "").strip()
        if not path_value or not time_value:
            continue
        try:
            accident_times[Path(path_value).name.lower()] = float(time_value)
        except ValueError:
            continue
    return accident_times


def get_period(timestamp: float, accident_time: float) -> str:
    before_start = accident_time - 2.0
    before_end = accident_time - 0.5
    accident_end = accident_time + 1.0
    after_end = accident_time + 2.0

    if before_start <= timestamp < before_end:
        return "antes"
    if before_end <= timestamp <= accident_end:
        return "acidente"
    if accident_end < timestamp <= after_end:
        return "depois"
    return "fora_janela"


def open_video_info(path: Path) -> float:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise OSError(f"Não foi possível abrir o vídeo: {path}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            raise ValueError(f"FPS inválido no vídeo: {path}")
        return fps
    finally:
        capture.release()


def analyze_video(model: YOLO, video_path: Path, accident_time: float) -> list[dict[str, Any]]:
    fps = open_video_info(video_path)
    predictions = model.predict(
        source=str(video_path),
        stream=True,
        save=False,
        conf=MIN_CONFIDENCE,
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False,
    )

    frame_rows: list[dict[str, Any]] = []
    for frame_index, result in enumerate(
        tqdm(predictions, desc=video_path.name, unit="frame", leave=True)
    ):
        timestamp = frame_index / fps
        boxes = result.boxes
        max_confidence = (
            float(boxes.conf.max().item()) if boxes is not None and len(boxes) else None
        )
        frame_rows.append(
            {
                "video": video_path.name,
                "frame": frame_index,
                "timestamp_seconds": round(timestamp, 6),
                "accident_time_seconds": accident_time,
                "period": get_period(timestamp, accident_time),
                "max_confidence": (
                    round(max_confidence, 6) if max_confidence is not None else ""
                ),
            }
        )
    return frame_rows


def print_summary(frame_rows: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in frame_rows:
        confidence = row["max_confidence"]
        if confidence != "" and row["period"] != "fora_janela":
            grouped[(row["video"], row["period"])].append(float(confidence))

    period_labels = ("antes", "acidente", "depois")
    print("\nResumo por vídeo e período (inferência mínima: 0.10)")
    for video_name in VIDEO_NAMES:
        print(f"\n{video_name}")
        for period in period_labels:
            confidences = grouped.get((video_name, period), [])
            highest = f"{max(confidences):.4f}" if confidences else "—"
            threshold_counts = [
                sum(value >= threshold for value in confidences)
                for threshold in CONFIDENCE_THRESHOLDS
            ]
            threshold_text = ", ".join(
                f">={threshold:.2f}: {count}"
                for threshold, count in zip(CONFIDENCE_THRESHOLDS, threshold_counts)
            )
            print(
                f"  {period:8} | maior confiança: {highest:>6} | "
                f"frames detectados (>=0.10): {len(confidences):3} | {threshold_text}"
            )


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    if not METADATA_ZIP.is_file():
        raise FileNotFoundError(f"ZIP de metadados não encontrado: {METADATA_ZIP}")

    accident_times = read_accident_times(METADATA_ZIP)
    videos: list[tuple[Path, float]] = []
    for name in VIDEO_NAMES:
        video_path = VIDEO_DIR / name
        if not video_path.is_file():
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")
        accident_time = accident_times.get(name.lower())
        if accident_time is None:
            raise KeyError(f"accident_time não encontrado no ZIP para {name}")
        videos.append((video_path, accident_time))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"candidate_confidence_{timestamp}.csv"

    print(f"Modelo: {MODEL_PATH}")
    print(f"Inferência: CUDA:{DEVICE}, imgsz={IMAGE_SIZE}, conf mínima={MIN_CONFIDENCE:.2f}")
    print(f"Metadados: {METADATA_ZIP} ({METADATA_ENTRY})")

    model = YOLO(str(MODEL_PATH))
    all_rows: list[dict[str, Any]] = []
    for index, (video_path, accident_time) in enumerate(videos, start=1):
        print(
            f"\n[{index}/{len(videos)}] {video_path.name} "
            f"(accident_time={accident_time:.3f}s)"
        )
        rows = analyze_video(model, video_path, accident_time)
        all_rows.extend(rows)
        print(f"Frames analisados: {len(rows)}")

    fieldnames = (
        "video",
        "frame",
        "timestamp_seconds",
        "accident_time_seconds",
        "period",
        "max_confidence",
        *(f"detected_at_{threshold:.2f}" for threshold in CONFIDENCE_THRESHOLDS),
    )
    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            confidence = row["max_confidence"]
            enriched = dict(row)
            for threshold in CONFIDENCE_THRESHOLDS:
                enriched[f"detected_at_{threshold:.2f}"] = int(
                    confidence != "" and float(confidence) >= threshold
                )
            writer.writerow(enriched)

    print_summary(all_rows)
    print(f"\nRelatório por frame salvo em: {report_path}")


if __name__ == "__main__":
    main()
