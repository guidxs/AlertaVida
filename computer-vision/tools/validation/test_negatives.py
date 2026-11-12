
import os
from pathlib import Path
from ultralytics import YOLO

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATASET = PROJECT_DIR / "dataset" / "processed_clean" / "Accident_Detection" / "Dataset"
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
MODEL = str((_model_path if _model_path.is_absolute() else PROJECT_DIR / _model_path).resolve())

model = YOLO(MODEL)

labels_dir = DATASET / "test" / "labels"
images_dir = DATASET / "test" / "images"

# Localiza imagens cujas anotações estão vazias
negative_labels = [
    p for p in labels_dir.glob("*.txt")
    if p.stat().st_size == 0
]

images = []
for label in negative_labels:
    matches = list(images_dir.glob(label.stem + ".*"))
    if matches:
        images.append(str(matches[0]))

print(f"Imagens negativas encontradas: {len(images)}")

# Executa as detecções
results = model.predict(
    source=images,
    conf=0.25,
    imgsz=640,
    device=0,
    save=True,
    project=str(PROJECT_DIR / "results"),
    name="negative_test",
    exist_ok=True
)

print("\nRESULTADOS:")
for result in results:
    boxes = result.boxes
    confidences = boxes.conf.tolist() if boxes is not None else []

    print(
        f"{Path(result.path).name}: "
        f"{len(confidences)} detecções"
        + (
            f" | maior confiança: {max(confidences):.2f}"
            if confidences else ""
        )
    )

print("\nTeste concluído!")
