"""Train AlertaVida's custom accident detector from project-relative inputs."""

import argparse
from pathlib import Path

from ultralytics import YOLO


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA = (
    PROJECT_DIR
    / "dataset"
    / "processed_clean"
    / "Accident_Detection"
    / "Dataset"
    / "data.yaml"
)
DEFAULT_MODEL = PROJECT_DIR / "models" / "yolo11n.pt"
DEFAULT_PROJECT = PROJECT_DIR / "runs" / "detect" / "runs"


def resolve_project_path(value: str | Path) -> Path:
    """Resolve relative CLI paths from the computer-vision project root."""
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina o detector customizado AlertaVida.")
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA),
        help="Caminho do data.yaml; caminhos relativos são resolvidos desde computer-vision/.",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help="Pesos base; caminhos relativos são resolvidos desde computer-vision/.",
    )
    parser.add_argument(
        "--project",
        default=str(DEFAULT_PROJECT),
        help="Pasta dos resultados; caminhos relativos são resolvidos desde computer-vision/.",
    )
    parser.add_argument("--name", default="alertavida_yolo11n", help="Nome da execução.")
    args = parser.parse_args()

    data_yaml = resolve_project_path(args.data)
    model_path = resolve_project_path(args.model)
    output_project = resolve_project_path(args.project)
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Configuração do dataset não encontrada: {data_yaml}")
    if not model_path.is_file():
        raise FileNotFoundError(f"Pesos base não encontrados: {model_path}")

    # Pass the absolute YAML path. Ultralytics uses its parent as the dataset root
    # when the YAML has no explicit `path`, so split paths work from any CWD.
    model = YOLO(str(model_path))
    model.train(
        data=str(data_yaml),
        epochs=80,
        imgsz=640,
        batch=8,
        device=0,
        workers=4,
        cache=False,
        patience=15,
        project=str(output_project),
        name=args.name,
        exist_ok=False,
        pretrained=True,
        save=True,
        plots=True,
        seed=42,
    )

    print("\nTreinamento concluído!")
    print(f"Melhores pesos: {output_project / args.name / 'weights' / 'best.pt'}")


if __name__ == "__main__":
    main()
