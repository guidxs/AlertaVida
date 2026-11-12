"""Create a side-by-side visual review sheet for selected batch 2 videos."""

import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[2]
METADATA_ZIP = PROJECT_DIR / "videos" / "archive.zip"
ORIGINAL_DIR = PROJECT_DIR / "videos" / "candidates_batch2"
PROCESSED_DIR = PROJECT_DIR / "videos" / "candidates_batch2_output"
REVIEW_DIR = PROJECT_DIR / "videos" / "review" / "batch2"
METADATA_ENTRY = "metadata-real.csv"

VIDEO_NAMES = (
    "BpMHNEa79lo_4_00.mp4",
    "hdyWKrR5uCk_00.mp4",
    "L334aqEJxys_0_00.mp4",
    "mhQIf0yVU3g_3_00.mp4",
    "N6zJ2inqJn0_0_00.mp4",
    "nEszisiy2ho_00.mp4",
    "OehnhIPFm4Q_04.mp4",
    "oV7t0yEbT8c_00.mp4",
    "russia16_00.mp4",
    "TXZfPbiopOE_00.mp4",
    "y4Evv5By6sg_1_00.mp4",
    "y4Evv5By6sg_4_00.mp4",
)
SUPPORTED_VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm"}
THUMBNAIL_SIZE = (320, 180)
LABEL_HEIGHT = 34
MOMENTS = ((-1, "-1s"), (0, "acidente"), (1, "+1s"))


def load_accident_times(zip_path: Path) -> dict[str, float]:
    """Read accident_time from the CSV inside the ZIP without extracting it."""
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
    if not reader.fieldnames or "path" not in reader.fieldnames or "accident_time" not in reader.fieldnames:
        raise ValueError("metadata-real.csv precisa conter as colunas path e accident_time.")

    times: dict[str, float] = {}
    for row in reader:
        source_path = (row.get("path") or "").strip().replace("\\", "/")
        value = (row.get("accident_time") or "").strip()
        if not source_path or not value:
            continue
        try:
            times[Path(source_path).name.lower()] = float(value)
        except ValueError:
            continue
    return times


def find_video(directory: Path, filename: str) -> Path | None:
    """Find a video by stem, allowing an output extension different from MP4."""
    stem = Path(filename).stem.lower()
    if not directory.is_dir():
        return None
    for path in directory.iterdir():
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
            and path.stem.lower() == stem
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


def make_cell(frame: np.ndarray | None, label: str, missing_text: str) -> np.ndarray:
    if frame is None:
        frame = np.full((THUMBNAIL_SIZE[1], THUMBNAIL_SIZE[0], 3), 35, dtype=np.uint8)
        cv2.putText(
            frame,
            missing_text,
            (14, THUMBNAIL_SIZE[1] // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (185, 185, 185),
            1,
            cv2.LINE_AA,
        )

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
    return np.vstack((band, frame))


def create_sheet(accident_times: dict[str, float]) -> tuple[np.ndarray, list[str]]:
    warnings: list[str] = []
    sheet_rows: list[np.ndarray] = []
    column_labels = [
        label
        for _, moment in MOMENTS
        for label in (f"Original {moment}", f"Processado {moment}")
    ]
    grid_width = THUMBNAIL_SIZE[0] * len(column_labels)

    header = np.full((44, grid_width, 3), 17, dtype=np.uint8)
    for column, label in enumerate(column_labels):
        cv2.putText(
            header,
            label,
            (column * THUMBNAIL_SIZE[0] + 10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (95, 190, 245),
            1,
            cv2.LINE_AA,
        )
    sheet_rows.append(header)

    for index, filename in enumerate(VIDEO_NAMES, start=1):
        accident_time = accident_times.get(filename.lower())
        if accident_time is None:
            warnings.append(f"accident_time não encontrado no ZIP para {filename}; vídeo ignorado.")
            continue

        original_path = find_video(ORIGINAL_DIR, filename)
        processed_path = find_video(PROCESSED_DIR, filename)
        if original_path is None:
            warnings.append(f"Original não encontrado: {filename} em {ORIGINAL_DIR}.")
        if processed_path is None:
            warnings.append(f"Processado não encontrado: {filename} em {PROCESSED_DIR}.")

        cells: list[np.ndarray] = []
        for offset, moment in MOMENTS:
            timestamp = max(0.0, accident_time + offset)
            timestamp_label = f"{timestamp:.2f}s"
            original_frame = read_frame_at(original_path, timestamp) if original_path else None
            processed_frame = read_frame_at(processed_path, timestamp) if processed_path else None
            if original_path and original_frame is None:
                warnings.append(f"Não foi possível ler {original_path.name} em {timestamp_label}.")
            if processed_path and processed_frame is None:
                warnings.append(f"Não foi possível ler {processed_path.name} em {timestamp_label}.")

            cells.append(make_cell(original_frame, f"Original | {moment} | {timestamp_label}", "Original indisponível"))
            cells.append(make_cell(processed_frame, f"YOLO | {moment} | {timestamp_label}", "Processado indisponível"))

        video_header = np.full((34, grid_width, 3), 28, dtype=np.uint8)
        cv2.putText(
            video_header,
            f"{index:02d}. {filename}  |  accident_time: {accident_time:.2f}s",
            (12, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
        sheet_rows.extend((video_header, np.hstack(cells)))
        print(f"[{index}/{len(VIDEO_NAMES)}] Frames capturados: {filename}")

    if len(sheet_rows) == 1:
        raise ValueError("Nenhum vídeo pôde ser incluído na contact sheet.")
    return np.vstack(sheet_rows), warnings


def main() -> None:
    if not METADATA_ZIP.is_file():
        raise FileNotFoundError(f"ZIP de metadados não encontrado: {METADATA_ZIP}")
    accident_times = load_accident_times(METADATA_ZIP)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    sheet, warnings = create_sheet(accident_times)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = REVIEW_DIR / f"review_sheet_batch2_{timestamp}.jpg"
    suffix = 1
    while output_path.exists():
        output_path = REVIEW_DIR / f"review_sheet_batch2_{timestamp}_{suffix}.jpg"
        suffix += 1

    if not cv2.imwrite(str(output_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise OSError(f"Não foi possível salvar a imagem: {output_path}")

    print(f"\nContact sheet salva em: {output_path}")
    print(f"Metadados utilizados: {METADATA_ZIP} ({METADATA_ENTRY})")
    if warnings:
        print("\nAvisos:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("Todos os vídeos e frames solicitados foram encontrados e lidos.")


if __name__ == "__main__":
    main()
