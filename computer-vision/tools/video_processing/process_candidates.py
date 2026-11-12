"""Run the trained AlertaVida detector over the selected candidate videos."""

import json
import os
from pathlib import Path
from typing import Any

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
INPUT_DIR = PROJECT_DIR / "videos" / "candidates"
OUTPUT_DIR = PROJECT_DIR / "videos" / "candidates_output"
METRICS_PATH = OUTPUT_DIR / "metrics.json"

CONFIDENCE = 0.50
IMAGE_SIZE = 640
DEVICE = 0


def process_video(model: YOLO, video_path: Path) -> dict[str, Any]:
    """Infer one video as a stream, keeping only aggregate metrics in memory."""
    total_frames = 0
    frames_with_detection = 0
    highest_confidence: float | None = None

    predictions = model.predict(
        source=str(video_path),
        stream=True,
        save=True,
        project=str(OUTPUT_DIR.parent),
        name=OUTPUT_DIR.name,
        exist_ok=True,
        conf=CONFIDENCE,
        imgsz=IMAGE_SIZE,
        device=DEVICE,
        verbose=False,
    )

    for result in tqdm(predictions, desc=video_path.name, unit="frame", leave=True):
        total_frames += 1
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue

        frames_with_detection += 1
        frame_max = float(boxes.conf.max().item())
        if highest_confidence is None or frame_max > highest_confidence:
            highest_confidence = frame_max

    detection_percentage = (
        (frames_with_detection / total_frames) * 100 if total_frames else 0.0
    )

    return {
        "nome": video_path.name,
        "quantidade_quadros": total_frames,
        "quadros_com_deteccao": frames_with_detection,
        "percentual_quadros_com_deteccao": round(detection_percentage, 2),
        "maior_confianca": (
            round(highest_confidence, 6) if highest_confidence is not None else None
        ),
    }


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    if not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Pasta de vídeos não encontrada: {INPUT_DIR}")

    videos = sorted(INPUT_DIR.glob("*.mp4"), key=lambda path: path.name.lower())
    if not videos:
        raise FileNotFoundError(f"Nenhum arquivo MP4 encontrado em {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Modelo: {MODEL_PATH}")
    print(f"Dispositivo: CUDA:{DEVICE} | confiança: {CONFIDENCE:.2f} | imgsz: {IMAGE_SIZE}")
    print(f"Vídeos encontrados: {len(videos)}\n")

    model = YOLO(str(MODEL_PATH))
    metrics = []

    for index, video_path in enumerate(videos, start=1):
        print(f"\n[{index}/{len(videos)}] Processando {video_path.name}")
        item = process_video(model, video_path)
        metrics.append(item)
        confidence = (
            f"{item['maior_confianca']:.4f}"
            if item["maior_confianca"] is not None
            else "sem detecções"
        )
        print(
            f"Concluído: {item['quantidade_quadros']} quadros; "
            f"{item['quadros_com_deteccao']} com detecção "
            f"({item['percentual_quadros_com_deteccao']:.2f}%); "
            f"maior confiança: {confidence}."
        )

    report = {
        "modelo": str(MODEL_PATH),
        "parametros": {
            "device": DEVICE,
            "conf": CONFIDENCE,
            "imgsz": IMAGE_SIZE,
        },
        "videos": metrics,
    }
    METRICS_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nRelatório salvo em: {METRICS_PATH}")
    print(f"Vídeos processados salvos em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
