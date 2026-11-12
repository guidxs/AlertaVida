import os
from pathlib import Path
import cv2
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

VIDEOS = {
    "vxZ47DoPNY8_00.mp4": 2.833,
    "kABWTDKgc9U_00.mp4": 6.566,
    "-SNFUobKjoM_00.mp4": 13.533,
}

model = YOLO(str(MODEL_PATH))

for name, accident_time in VIDEOS.items():
    path = INPUT_DIR / name
    cap = cv2.VideoCapture(str(path))

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_index = 0
    event_results = []
    other_results = []

    print(f"\n===== {name} =====")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % 6 == 0:
            timestamp = frame_index / fps

            result = model.predict(
                frame,
                conf=0.50,
                device=0,
                verbose=False
            )[0]

            count = len(result.boxes)
            max_conf = (
                float(result.boxes.conf.max())
                if count else 0
            )

            data = (timestamp, count, max_conf)

            if abs(timestamp - accident_time) <= 1.5:
                event_results.append(data)
            else:
                other_results.append(data)

        frame_index += 1

    cap.release()

    print(f"Momento do acidente: {accident_time:.2f}s")
    print(f"Quadros próximos ao acidente: {len(event_results)}")
    print(f"Detecções próximas: {sum(x[1] for x in event_results)}")
    print(f"Maior confiança próxima: {max((x[2] for x in event_results), default=0):.2f}")
    print(f"Detecções no restante: {sum(x[1] for x in other_results)}")
    print(f"Quadros analisados no restante: {len(other_results)}")

print("\nAnálise concluída!")
