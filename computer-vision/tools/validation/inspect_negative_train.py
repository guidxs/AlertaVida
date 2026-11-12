from pathlib import Path
import cv2
import math

PROJECT_DIR = Path(__file__).resolve().parents[2]
dataset = PROJECT_DIR / "dataset" / "processed_clean" / "Accident_Detection" / "Dataset"

labels_dir = dataset / "train" / "labels"
images_dir = dataset / "train" / "images"
output_dir = PROJECT_DIR / "evidence" / "negative_train"

output_dir.mkdir(parents=True, exist_ok=True)

negatives = sorted(
    p for p in labels_dir.glob("*.txt")
    if p.stat().st_size == 0
)

print(f"Total de imagens negativas: {len(negatives)}")

for batch_number, start in enumerate(range(0, len(negatives), 30), 1):
    batch = negatives[start:start + 30]
    cards = []

    for label in batch:
        matches = list(images_dir.glob(label.stem + ".*"))

        if not matches:
            print(f"Imagem nao encontrada: {label.stem}")
            continue

        image = cv2.imread(str(matches[0]))

        if image is None:
            print(f"Erro ao ler: {label.stem}")
            continue

        image = cv2.resize(image, (240, 180))

        cv2.putText(
            image,
            label.stem,
            (6, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1
        )

        cards.append(image)

    columns = 5
    rows = math.ceil(len(cards) / columns)
    blank = 255 * (cards[0] * 0 + 1) if cards else None

    while len(cards) < rows * columns:
        cards.append(blank.copy())

    grid = cv2.vconcat([
        cv2.hconcat(cards[i:i + columns])
        for i in range(0, len(cards), columns)
    ])

    output = output_dir / f"batch_{batch_number:02d}.jpg"
    cv2.imwrite(str(output), grid)

    print(f"Grupo {batch_number}: {output}")

print("Auditoria visual preparada!")
