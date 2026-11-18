
from pathlib import Path
import os
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
INPUT_DIR = PROJECT_DIR / "videos" / "input"
OUTPUT_DIR = PROJECT_DIR / "videos" / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Carrega o modelo treinado
model = YOLO(str(MODEL_PATH))

# Analisa todos os vídeos da pasta
videos = list(INPUT_DIR.glob("*.mp4"))

if not videos:
    print("Nenhum vídeo encontrado.")
    raise SystemExit

for video in videos:
    print(f"\nAnalisando: {video.name}")

    results = model.predict(
        source=str(video),
        conf=0.65,
        imgsz=640,
        device=0,
        save=True,
        project=str(OUTPUT_DIR),
        name=video.stem,
        exist_ok=True,
        verbose=False
    )

    total_frames = len(results)
    frames_detected = sum(len(result.boxes) > 0 for result in results)

    print(f"Frames analisados: {total_frames}")
    print(f"Frames com detecção: {frames_detected}")
    print(f"Vídeo processado: {video.name}")

print("\nTestes concluídos!")
