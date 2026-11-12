
from pathlib import Path
from PIL import Image, ImageDraw
import random
import math

PROJECT_DIR = Path(__file__).resolve().parents[2]
BASE = PROJECT_DIR / "dataset" / "processed_clean" / "Accident_Detection" / "Dataset"
OUTPUT = PROJECT_DIR / "results" / "revisao_treino.png"

IMAGES = BASE / "train" / "images"
LABELS = BASE / "train" / "labels"

random.seed(42)

files = list(IMAGES.glob("*"))
sample = random.sample(files, min(100, len(files)))

columns = 10
cell_width = 160
cell_height = 150
rows = math.ceil(len(sample) / columns)

sheet = Image.new(
    "RGB",
    (columns * cell_width, rows * cell_height),
    "white"
)

draw = ImageDraw.Draw(sheet)

for index, image_path in enumerate(sample):
    try:
        image = Image.open(image_path).convert("RGB")
        image.thumbnail((150, 115))

        label_path = LABELS / f"{image_path.stem}.txt"
        status = "POSITIVA" if label_path.exists() and label_path.stat().st_size > 0 else "NEGATIVA"

        x = (index % columns) * cell_width
        y = (index // columns) * cell_height

        sheet.paste(image, (x + 5, y + 5))
        draw.text((x + 5, y + 122), image_path.stem[:18], fill="black")
        draw.text((x + 5, y + 136), status, fill="green" if status == "POSITIVA" else "red")

    except Exception as error:
        print(f"Erro em {image_path.name}: {error}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUTPUT)

print(f"Amostra criada: {OUTPUT}")
print(f"Imagens analisadas: {len(sample)}")
