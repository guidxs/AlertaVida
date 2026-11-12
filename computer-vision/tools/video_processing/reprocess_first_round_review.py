"""Reprocess three first-round videos and create a visual review sheet."""

import csv
import io
import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe
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
ORIGINAL_DIR = PROJECT_DIR / "videos" / "candidates"
METADATA_ZIP = PROJECT_DIR / "videos" / "archive.zip"
OUTPUT_DIR = PROJECT_DIR / "videos" / "first_round_review_conf070"
AVI_DIR = OUTPUT_DIR / "intermediate_avi"
MP4_DIR = OUTPUT_DIR / "processed"
METRICS_PATH = OUTPUT_DIR / "metrics.json"
SHEET_PATH = OUTPUT_DIR / "contact_sheet.jpg"

VIDEO_NAMES = (
    "e17Wq4Hpqlk_02.mp4",
    "N6zJ2inqJn0_3_00.mp4",
    "q7UutMH5DTM_00.mp4",
)
CONFIDENCE = 0.70
IMAGE_SIZE = 640
DEVICE = 0
THUMBNAIL_SIZE = (320, 180)
LABEL_HEIGHT = 34


def parse_accident_times() -> dict[str, float]:
    """Read video accident times from metadata-real.csv without extracting it."""
    with zipfile.ZipFile(METADATA_ZIP) as archive:
        csv_bytes = archive.read("metadata-real.csv")
    csv_text = csv_bytes.decode("utf-8-sig")
    sample = csv_text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(csv_text, newline=""), dialect=dialect)
    rows = list(reader)
    if not rows:
        raise ValueError("metadata-real.csv não contém linhas de dados.")

    def normalized(value: str | None) -> str:
        return "".join(char for char in (value or "").lower() if char.isalnum())

    time_column = next((key for key in rows[0] if normalized(key) == "accidenttime"), None)
    if time_column is None:
        raise ValueError("Coluna accident_time não encontrada em metadata-real.csv.")
    video_columns = [
        key for key in rows[0]
        if normalized(key) in {"video", "videoname", "videofile", "filename", "filepath", "file", "name"}
    ]
    times: dict[str, float] = {}
    for row in rows:
        raw_time = str(row.get(time_column) or "").strip().replace(",", ".")
        if not raw_time:
            continue
        try:
            if ":" in raw_time:
                parts = [float(part) for part in raw_time.split(":")]
                accident_time = parts[-1] + (parts[-2] * 60 if len(parts) >= 2 else 0)
                if len(parts) == 3:
                    accident_time += parts[0] * 3600
            else:
                accident_time = float(raw_time)
        except ValueError:
            continue
        names = [row.get(column, "") for column in video_columns]
        names.extend(
            value for key, value in row.items()
            if key != time_column and value and str(value).lower().endswith(
                (".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm")
            )
        )
        for name in names:
            name = str(name or "").strip().replace("\\", "/")
            if name:
                times[Path(name).stem.lower()] = accident_time
    return times


def find_video(directory: Path, stem: str) -> Path | None:
    if not directory.is_dir():
        return None
    return next(
        (path for path in directory.rglob("*") if path.is_file() and path.stem.lower() == stem.lower()
         and path.suffix.lower() in {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm"}),
        None,
    )


def process_video(model: YOLO, source: Path) -> dict[str, Any]:
    total_frames = 0
    frames_with_detection = 0
    max_confidence: float | None = None
    results = model.predict(
        source=str(source),
        stream=True,
        save=True,
        project=str(AVI_DIR),
        name=source.stem,
        exist_ok=True,
        conf=CONFIDENCE,
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False,
    )
    for result in tqdm(results, desc=source.name, unit="frame"):
        total_frames += 1
        if result.boxes is None or len(result.boxes) == 0:
            continue
        frames_with_detection += 1
        frame_confidence = float(result.boxes.conf.max().item())
        max_confidence = max(max_confidence or 0.0, frame_confidence)
    return {
        "nome": source.name,
        "quantidade_quadros": total_frames,
        "quadros_com_deteccao": frames_with_detection,
        "percentual_quadros_com_deteccao": round(100 * frames_with_detection / total_frames, 2)
        if total_frames else 0.0,
        "maior_confianca": round(max_confidence, 6) if max_confidence is not None else None,
        "accident_time_seconds": None,
        "original": str(source.relative_to(PROJECT_DIR)).replace("\\", "/"),
        "processed_mp4": None,
        "browser_compatible": False,
    }


def convert_to_browser_mp4(avi_path: Path, mp4_path: Path) -> None:
    """Convert only after a successful H.264 encode; leave source AVI intact."""
    ffmpeg = get_ffmpeg_exe()
    temporary_path = mp4_path.with_name(mp4_path.stem + ".partial.mp4")
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(avi_path),
        "-map", "0:v:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-f", "mp4", str(temporary_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not temporary_path.is_file() or temporary_path.stat().st_size == 0:
        temporary_path.unlink(missing_ok=True)
        detail = completed.stderr.strip() or f"código de saída {completed.returncode}"
        raise RuntimeError(f"Falha na conversão de {avi_path.name}: {detail}")
    temporary_path.replace(mp4_path)


def read_frame(path: Path | None, seconds: float) -> np.ndarray | None:
    if path is None:
        return None
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


def labeled_cell(frame: np.ndarray | None, label: str) -> np.ndarray:
    if frame is None:
        frame = np.full((THUMBNAIL_SIZE[1], THUMBNAIL_SIZE[0], 3), 38, dtype=np.uint8)
        cv2.putText(frame, "Frame indisponível", (14, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    (190, 190, 190), 1, cv2.LINE_AA)
    band = np.full((LABEL_HEIGHT, THUMBNAIL_SIZE[0], 3), 22, dtype=np.uint8)
    cv2.putText(band, label, (9, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                (235, 240, 245), 1, cv2.LINE_AA)
    return np.vstack((band, frame))


def create_contact_sheet(items: list[dict[str, Any]]) -> None:
    column_labels = ("Original −1s", "YOLO −1s", "Original acidente", "YOLO acidente",
                     "Original +1s", "YOLO +1s")
    width = THUMBNAIL_SIZE[0] * len(column_labels)
    rows: list[np.ndarray] = []
    header = np.full((44, width, 3), 17, dtype=np.uint8)
    for column, label in enumerate(column_labels):
        cv2.putText(header, label, (column * THUMBNAIL_SIZE[0] + 10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.56, (95, 190, 245), 1, cv2.LINE_AA)
    rows.append(header)

    for index, item in enumerate(items, start=1):
        original = PROJECT_DIR / item["original"]
        processed = OUTPUT_DIR / item["processed_mp4"] if item["processed_mp4"] else None
        accident_time = float(item["accident_time_seconds"])
        cells: list[np.ndarray] = []
        for offset, label in ((-1, "−1s"), (0, "acidente"), (1, "+1s")):
            target = max(0.0, accident_time + offset)
            stamp = f"{target:.2f}s"
            cells.append(labeled_cell(read_frame(original, target), f"{label} | {stamp} | original"))
            cells.append(labeled_cell(read_frame(processed, target), f"{label} | {stamp} | YOLO"))
        row_header = np.full((36, width, 3), 28, dtype=np.uint8)
        cv2.putText(row_header, f"{index:02d}. {item['nome']} | accident_time: {accident_time:.3f}s",
                    (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (245, 245, 245), 1, cv2.LINE_AA)
        rows.extend((row_header, np.hstack(cells)))
    if not cv2.imwrite(str(SHEET_PATH), np.vstack(rows)):
        raise OSError(f"Não foi possível salvar a folha de comparação: {SHEET_PATH}")


def main() -> None:
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"A pasta de saída já existe; para preservar arquivos, não será sobrescrita: {OUTPUT_DIR}"
        )
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    if not METADATA_ZIP.is_file():
        raise FileNotFoundError(f"ZIP de metadados não encontrado: {METADATA_ZIP}")

    accident_times = parse_accident_times()
    sources: list[tuple[Path, float]] = []
    for name in VIDEO_NAMES:
        source = ORIGINAL_DIR / name
        if not source.is_file():
            raise FileNotFoundError(f"Vídeo original não encontrado: {source}")
        accident_time = accident_times.get(source.stem.lower())
        if accident_time is None:
            raise ValueError(f"accident_time não encontrado no ZIP para {name}")
        sources.append((source, accident_time))

    OUTPUT_DIR.mkdir(parents=True)
    AVI_DIR.mkdir()
    MP4_DIR.mkdir()
    print(f"Modelo: {MODEL_PATH}")
    print(f"CUDA:{DEVICE} | confiança: {CONFIDENCE:.2f} | imgsz: {IMAGE_SIZE}")
    print(f"Saída separada: {OUTPUT_DIR}")
    model = YOLO(str(MODEL_PATH))
    report_items: list[dict[str, Any]] = []
    failures: list[str] = []

    for index, (source, accident_time) in enumerate(sources, start=1):
        print(f"\n[{index}/{len(sources)}] Processando {source.name}")
        item = process_video(model, source)
        item["accident_time_seconds"] = accident_time
        avi_path = find_video(AVI_DIR, source.stem)
        if avi_path is None:
            failures.append(f"{source.name}: AVI processado não encontrado em {AVI_DIR}")
        else:
            mp4_path = MP4_DIR / f"{source.stem}.mp4"
            try:
                convert_to_browser_mp4(avi_path, mp4_path)
                item["processed_mp4"] = str(mp4_path.relative_to(OUTPUT_DIR)).replace("\\", "/")
                item["browser_compatible"] = True
            except Exception as error:
                failures.append(str(error))
        report_items.append(item)
        print(f"Quadros: {item['quantidade_quadros']} | detectados: {item['quadros_com_deteccao']} "
              f"({item['percentual_quadros_com_deteccao']:.2f}%) | confiança máxima: "
              f"{item['maior_confianca'] if item['maior_confianca'] is not None else 'sem detecções'}")

    report = {
        "modelo": str(MODEL_PATH),
        "parametros": {"device": DEVICE, "conf": CONFIDENCE, "imgsz": IMAGE_SIZE},
        "metadados_origem": str(METADATA_ZIP.relative_to(PROJECT_DIR)).replace("\\", "/"),
        "videos": report_items,
        "falhas": failures,
    }
    METRICS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    create_contact_sheet(report_items)
    print(f"\nMétricas: {METRICS_PATH}")
    print(f"Folha de comparação: {SHEET_PATH}")
    print(f"Vídeos MP4 convertidos: {sum(item['browser_compatible'] for item in report_items)}/{len(report_items)}")
    for failure in failures:
        print(f"AVISO: {failure}")


if __name__ == "__main__":
    main()
