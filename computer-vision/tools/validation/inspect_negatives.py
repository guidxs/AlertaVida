
from pathlib import Path
import cv2
import math

PROJECT_DIR = Path(__file__).resolve().parents[2]
dataset = PROJECT_DIR / "dataset" / "processed_clean" / "Accident_Detection" / "Dataset"

labels_dir = dataset / "test" / "labels"
images_dir = dataset / "test" / "images"

negatives = sorted(
    p for p in labels_dir.glob("*.txt")
    if p.stat().st_size == 0
)

cards = []

for label in negatives:
    matches = list(images_dir.glob(label.stem + ".*"))

    if not matches:
        continue

    image = cv2.imread(str(matches[0]))

    if image is None:
        continue

    image = cv2.resize(image, (320, 240))
    cv2.putText(
        image,
        label.stem,
        (8, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2
    )

    cards.append(image)

columns = 3
rows = math.ceil(len(cards) / columns)

canvas = cv2.vconcat([
    cv2.hconcat(
        cards[i:i + columns] +
        [cv2.resize(cards[0], (320, 240))] *
        (columns - len(cards[i:i + columns]))
    )
    for i in range(0, len(cards), columns)
])

output = PROJECT_DIR / "evidence" / "negative_audit.jpg"
output.parent.mkdir(exist_ok=True)

cv2.imwrite(str(output), canvas)
print(f"Imagens analisadas: {len(cards)}")
print(f"Arquivo salvo: {output.resolve()}")
