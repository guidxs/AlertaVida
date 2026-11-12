
from pathlib import Path
from collections import defaultdict
from PIL import Image
import hashlib

PROJECT_DIR = Path(__file__).resolve().parents[2]
BASE = PROJECT_DIR / "dataset" / "processed_clean" / "Accident_Detection" / "Dataset"
groups = defaultdict(list)

# Identifica imagens idênticas
for split in ["train", "valid", "test"]:
    folder = BASE / split / "images"

    for path in folder.iterdir():
        if not path.is_file():
            continue

        try:
            with Image.open(path) as img:
                digest = hashlib.sha256(img.convert("RGB").tobytes()).hexdigest()
                groups[digest].append((split, path.name))
        except Exception:
            print(f"Imagem inválida: {path}")

duplicates = [items for items in groups.values() if len(items) > 1]

cross_split = [
    items for items in duplicates
    if len(set(split for split, _ in items)) > 1
]

# Compara as anotações das imagens duplicadas
same = 0
different = 0

for group in cross_split:
    annotations = []

    for split, name in group:
        label_path = BASE / split / "labels" / f"{Path(name).stem}.txt"

        if label_path.exists():
            content = sorted(
                line.strip()
                for line in label_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        else:
            content = None

        annotations.append(content)

    if all(annotation == annotations[0] for annotation in annotations):
        same += 1
    else:
        different += 1

print("\n===== ANÁLISE DAS DUPLICATAS =====")
print(f"Grupos duplicados: {len(duplicates)}")
print(f"Duplicatas entre divisões: {len(cross_split)}")
print(f"Anotações iguais: {same}")
print(f"Anotações diferentes ou ausentes: {different}")

print("\n===== EXEMPLOS COM ANOTAÇÕES DIFERENTES =====")

shown = 0

for group in cross_split:
    annotations = []

    for split, name in group:
        label_path = BASE / split / "labels" / f"{Path(name).stem}.txt"

        content = (
            label_path.read_text(encoding="utf-8").strip()
            if label_path.exists()
            else "SEM LABEL"
        )

        annotations.append(content)

    if not all(a == annotations[0] for a in annotations):
        print("\nGrupo:")
        for (split, name), annotation in zip(group, annotations):
            print(f"{split}/{name}: {annotation[:200]}")

        shown += 1

    if shown == 10:
        break
