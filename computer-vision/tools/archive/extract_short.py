"""Legacy dataset extraction utility retained for provenance."""

import zipfile
from pathlib import Path, PurePosixPath


PROJECT_DIR = Path(__file__).resolve().parents[2]
ZIP_PATH = PROJECT_DIR / "dataset" / "raw" / "Accident_Detection.zip"
OUTPUT_DIR = PROJECT_DIR / "dataset" / "processed_clean"

with zipfile.ZipFile(ZIP_PATH) as archive:
    files = [item for item in archive.infolist() if not item.is_dir()]
    names = {}
    counter = 0

    # Cria nomes curtos para as imagens.
    for item in files:
        path = PurePosixPath(item.filename)
        if "images" in path.parts:
            split = path.parts[-3]
            key = (split, path.stem)
            if key not in names:
                counter += 1
                names[key] = f"img_{counter:05d}"

    # Extrai mantendo a correspondência entre imagens e labels.
    for item in files:
        path = PurePosixPath(item.filename)
        parts = list(path.parts)

        if "images" in parts:
            split = parts[parts.index("images") - 1]
            parts[-1] = names[(split, path.stem)] + path.suffix.lower()
        elif "labels" in parts:
            split = parts[parts.index("labels") - 1]
            key = (split, path.stem)
            if key in names:
                parts[-1] = names[key] + ".txt"

        destination = OUTPUT_DIR.joinpath(*parts)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with archive.open(item) as source, destination.open("wb") as target:
            target.write(source.read())

print(f"Extração concluída! {counter} imagens com nomes curtos.")
