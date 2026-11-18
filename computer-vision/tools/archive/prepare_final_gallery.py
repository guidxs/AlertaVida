"""Build a ten-video AlertaVida gallery with confidence 0.70 results."""

import csv
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
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
METADATA_ZIP = PROJECT_DIR / "videos" / "archive.zip"
FIRST_ORIGINALS = PROJECT_DIR / "videos" / "candidates"
FIRST_RESULTS = PROJECT_DIR / "videos" / "first_round_review_conf070"
SECOND_ORIGINALS = PROJECT_DIR / "videos" / "candidates_batch2"
GALLERY_DIR = PROJECT_DIR / "videos" / "gallery"
CURRENT_MANIFEST = GALLERY_DIR / "gallery.json"

CONFIDENCE = 0.70
IMAGE_SIZE = 640
DEVICE = 0
VIDEO_EXTENSIONS = {".avi", ".mp4", ".mov", ".mkv", ".m4v", ".webm"}

FIRST_ROUND = (
    "e17Wq4Hpqlk_02",
    "N6zJ2inqJn0_3_00",
    "q7UutMH5DTM_00",
)
SECOND_ROUND_OBSERVATIONS = {
    "y4Evv5By6sg_1_00": "Boa detecção do acidente.",
    "y4Evv5By6sg_4_00": "Boa detecção do acidente.",
    "TXZfPbiopOE_00": "Boa detecção do acidente.",
    "russia16_00": "Detecta antes (0.60) e durante a colisão (0.65).",
    "OehnhIPFm4Q_04": "Detecta a derrapagem e depois a colisão.",
    "N6zJ2inqJn0_0_00": "Falso positivo antes (0.78), mas detecta a colisão (0.80).",
    "L334aqEJxys_0_00": "Boa detecção do acidente.",
}
SECOND_ROUND = tuple(SECOND_ROUND_OBSERVATIONS)
FIRST_ROUND_OBSERVATION = "Resultado reprocessado com confiança mínima de 0,70; revisar visualmente."


def timestamp_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_metadata() -> dict[str, dict[str, Any]]:
    with zipfile.ZipFile(METADATA_ZIP, "r") as archive:
        csv_text = archive.read("metadata-real.csv").decode("utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(csv_text[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(csv_text, newline=""), dialect=dialect)
    required = {"path", "type", "duration", "accident_time", "width", "height"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"Colunas esperadas ausentes em metadata-real.csv: {required}")
    return {
        Path(str(row.get("path", "")).replace("\\", "/")).stem.lower(): row
        for row in reader
        if row.get("path")
    }


def find_video(directory: Path, stem: str) -> Path:
    matches = [
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        and path.stem.lower() == stem.lower()
    ] if directory.is_dir() else []
    if not matches:
        raise FileNotFoundError(f"Vídeo {stem} não encontrado em {directory}")
    if len(matches) != 1:
        raise RuntimeError(f"Mais de um arquivo corresponde a {stem} em {directory}: {matches}")
    return matches[0]


def load_first_round_results() -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    metrics_path = FIRST_RESULTS / "metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"Métricas da primeira rodada não encontradas: {metrics_path}")
    report = json.loads(metrics_path.read_text(encoding="utf-8"))
    parameters = report.get("parametros", {})
    if (parameters.get("device") != DEVICE or float(parameters.get("conf", -1)) != CONFIDENCE
            or parameters.get("imgsz") != IMAGE_SIZE):
        raise ValueError("Métricas da primeira rodada não registram conf=0.70, device=0 e imgsz=640.")
    expected = {name.lower() for name in FIRST_ROUND}
    metrics = {Path(item["nome"]).stem.lower(): item for item in report.get("videos", [])}
    if set(metrics) != expected:
        raise ValueError("metrics.json da primeira rodada não contém exatamente os três vídeos esperados.")

    outputs: dict[str, Path] = {}
    for stem in FIRST_ROUND:
        item = metrics[stem.lower()]
        if item.get("browser_compatible") is not True or not item.get("processed_mp4"):
            raise ValueError(f"Resultado MP4 da primeira rodada não validado para {stem}.")
        video_path = FIRST_RESULTS / item["processed_mp4"]
        if not video_path.is_file():
            raise FileNotFoundError(f"MP4 reprocessado não encontrado para {stem}: {video_path}")
        outputs[stem.lower()] = video_path
    return metrics, outputs


def infer_one(model: YOLO, source: Path, avi_root: Path) -> dict[str, Any]:
    frame_count = 0
    detected_frames = 0
    max_confidence: float | None = None
    results = model.predict(
        source=str(source), stream=True, save=True,
        project=str(avi_root), name=source.stem, exist_ok=True,
        conf=CONFIDENCE, imgsz=IMAGE_SIZE, device=DEVICE, verbose=False,
    )
    for result in tqdm(results, desc=source.name, unit="frame", leave=True):
        frame_count += 1
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            continue
        detected_frames += 1
        confidence = float(boxes.conf.max().item())
        max_confidence = max(max_confidence or 0.0, confidence)
    return {
        "nome": source.name,
        "quantidade_quadros": frame_count,
        "quadros_com_deteccao": detected_frames,
        "percentual_quadros_com_deteccao": round(100 * detected_frames / frame_count, 2)
        if frame_count else 0.0,
        "maior_confianca": round(max_confidence, 6) if max_confidence is not None else None,
    }


def validate_metrics(item: dict[str, Any], name: str) -> None:
    total = int(item.get("quantidade_quadros", -1))
    detected = int(item.get("quadros_com_deteccao", -1))
    percentage = item.get("percentual_quadros_com_deteccao")
    confidence = item.get("maior_confianca")
    if total <= 0 or detected < 0 or detected > total:
        raise ValueError(f"Métricas inconsistentes para {name}: frames={total}, detectados={detected}.")
    expected_percentage = round(100 * detected / total, 2)
    if percentage is None or abs(float(percentage) - expected_percentage) > 0.011:
        raise ValueError(f"Percentual de frames inconsistente para {name}.")
    if confidence is not None and not (CONFIDENCE <= float(confidence) <= 1.0):
        raise ValueError(f"Maior confiança fora do intervalo configurado para {name}: {confidence}.")


def encode_h264(source: Path, destination: Path, ffmpeg: str) -> None:
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-map", "0:v:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-f", "mp4", str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        detail = result.stderr.strip() or f"código de saída {result.returncode}"
        raise RuntimeError(f"Conversão falhou: {source.name}: {detail}")


def top_level_mp4_atoms(path: Path) -> list[str]:
    atoms: list[str] = []
    file_size = path.stat().st_size
    with path.open("rb") as handle:
        position = 0
        while position + 8 <= file_size:
            handle.seek(position)
            header = handle.read(8)
            if len(header) < 8:
                break
            size = int.from_bytes(header[:4], "big")
            atom_type = header[4:8].decode("latin-1")
            header_size = 8
            if size == 1:
                extended_size = handle.read(8)
                if len(extended_size) != 8:
                    break
                size = int.from_bytes(extended_size, "big")
                header_size = 16
            elif size == 0:
                size = file_size - position
            if size < header_size or position + size > file_size:
                break
            atoms.append(atom_type)
            position += size
    return atoms


def validate_video(path: Path, expected_frames: int, ffmpeg: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"MP4 ausente ou vazio: {path}")
    probe = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True, check=False
    )
    probe_text = probe.stderr + probe.stdout
    if not re.search(r"Video:\s*h264\b", probe_text, re.IGNORECASE):
        raise RuntimeError(f"Codec H.264 não confirmado para {path.name}.")
    if not re.search(r"\byuv420p\b", probe_text, re.IGNORECASE):
        raise RuntimeError(f"Formato de pixel yuv420p não confirmado para {path.name}.")
    atoms = top_level_mp4_atoms(path)
    if "moov" not in atoms or "mdat" not in atoms or atoms.index("moov") > atoms.index("mdat"):
        raise RuntimeError(f"faststart (moov antes de mdat) não confirmado para {path.name}.")

    decode = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-map", "0:v:0", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    if decode.returncode != 0:
        raise RuntimeError(f"Falha ao decodificar {path.name} até o final: {decode.stderr.strip()}")
    capture = cv2.VideoCapture(str(path))
    decoded_frames = 0
    try:
        if not capture.isOpened():
            raise RuntimeError(f"OpenCV não conseguiu abrir {path.name}.")
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame is None or frame.size == 0:
                raise RuntimeError(f"Frame vazio durante leitura de {path.name}.")
            decoded_frames += 1
    finally:
        capture.release()
    if decoded_frames != expected_frames:
        raise RuntimeError(
            f"Leitura incompleta de {path.name}: {decoded_frames}/{expected_frames} frames."
        )
    return {"codec": "h264", "pixel_format": "yuv420p", "faststart": True,
            "decoded_frames": decoded_frames}


def make_manifest_entry(
    stem: str, observation: str, metadata: dict[str, Any], metric: dict[str, Any],
    original_relative: str, processed_relative: str,
) -> dict[str, Any]:
    validate_metrics(metric, stem)
    return {
        "name": stem,
        "accident_type": metadata["type"],
        "duration_seconds": float(metadata["duration"]),
        "accident_time_seconds": float(metadata["accident_time"]),
        "resolution": {"width": int(metadata["width"]), "height": int(metadata["height"])},
        "max_confidence": metric.get("maior_confianca"),
        "detected_frames_percentage": float(metric["percentual_quadros_com_deteccao"]),
        "detected_frames": int(metric["quadros_com_deteccao"]),
        "total_frames": int(metric["quantidade_quadros"]),
        "original_video": original_relative,
        "processed_video": processed_relative,
        "processed_video_mime_type": "video/mp4",
        "browser_compatible": True,
        "observation": observation,
    }


def free_backup_path(tag: str) -> Path:
    candidate = GALLERY_DIR / f"gallery.pre_conf070_{tag}.json"
    suffix = 1
    while candidate.exists():
        candidate = GALLERY_DIR / f"gallery.pre_conf070_{tag}_{suffix}.json"
        suffix += 1
    return candidate


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"Modelo não encontrado: {MODEL_PATH}")
    if not METADATA_ZIP.is_file() or not CURRENT_MANIFEST.is_file():
        raise FileNotFoundError("archive.zip ou gallery.json atual não foi encontrado.")
    if not (PROJECT_DIR / "videos" / "candidates_batch2").is_dir():
        raise FileNotFoundError(f"Originais da segunda rodada ausentes: {SECOND_ORIGINALS}")

    tag = timestamp_tag()
    inference_dir = PROJECT_DIR / "videos" / f"candidates_batch2_conf070_{tag}"
    staging_dir = GALLERY_DIR / f".staging_conf070_{tag}"
    release_name = f"conf070_{tag}"
    release_relative = Path("releases") / release_name
    release_dir = GALLERY_DIR / release_relative
    for path in (inference_dir, staging_dir, release_dir):
        if path.exists():
            raise FileExistsError(f"Para preservar arquivos, não será sobrescrita: {path}")

    metadata_by_stem = read_metadata()
    first_metrics, first_processed = load_first_round_results()
    sources: dict[str, Path] = {}
    for stem in FIRST_ROUND:
        sources[stem] = find_video(FIRST_ORIGINALS, stem)
    for stem in SECOND_ROUND:
        sources[stem] = find_video(SECOND_ORIGINALS, stem)
    expected_stems = set(FIRST_ROUND) | set(SECOND_ROUND)
    if len(sources) != 10 or set(sources) != expected_stems:
        raise RuntimeError("A seleção de entrada não corresponde aos dez vídeos pedidos.")
    for stem in sources:
        if stem.lower() not in metadata_by_stem:
            raise KeyError(f"Metadados não encontrados no ZIP para {stem}.")

    inference_dir.mkdir()
    avi_root = inference_dir / "avi"
    avi_root.mkdir()
    staging_dir.mkdir()
    staged_originals = staging_dir / "originals"
    staged_processed = staging_dir / "processed"
    staged_originals.mkdir()
    staged_processed.mkdir()
    ffmpeg = get_ffmpeg_exe()

    print(f"Modelo: {MODEL_PATH}")
    print(f"Inferência: conf={CONFIDENCE:.2f}, CUDA:{DEVICE}, imgsz={IMAGE_SIZE}")
    print(f"Serão inferidos somente os sete vídeos da segunda rodada.")
    model = YOLO(str(MODEL_PATH))
    second_metrics: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for index, stem in enumerate(SECOND_ROUND, start=1):
        source = sources[stem]
        print(f"\n[{index}/7] Processando {source.name}")
        metric = infer_one(model, source, avi_root)
        second_metrics[stem.lower()] = metric
        validate_metrics(metric, stem)
        avi = find_video(avi_root / source.stem, source.stem)
        target = staged_processed / f"{stem}.mp4"
        try:
            encode_h264(avi, target, ffmpeg)
            validation = validate_video(target, int(metric["quantidade_quadros"]), ffmpeg)
            metric["mp4_validation"] = validation
        except Exception as error:
            failures.append(f"{stem}: {error}")
            print(f"FALHA: {failures[-1]}")
            break
        print(f"Validado: {metric['quantidade_quadros']} frames; "
              f"{metric['quadros_com_deteccao']} com detecção; "
              f"confiança máxima {metric['maior_confianca']}.")

    if failures:
        raise RuntimeError("Manifesto não atualizado. " + failures[0])

    metrics_by_stem: dict[str, dict[str, Any]] = dict(first_metrics)
    metrics_by_stem.update(second_metrics)
    processed_sources: dict[str, Path] = dict(first_processed)
    for stem in SECOND_ROUND:
        processed_sources[stem.lower()] = staged_processed / f"{stem}.mp4"

    # Reuse first-round MP4 files by copying them into the staged release.
    for stem in FIRST_ROUND:
        destination = staged_processed / f"{stem}.mp4"
        shutil.copy2(first_processed[stem.lower()], destination)
        try:
            validation = validate_video(
                destination, int(first_metrics[stem.lower()]["quantidade_quadros"]), ffmpeg
            )
        except Exception as error:
            raise RuntimeError(f"{stem}: validação do MP4 existente falhou; manifesto não atualizado: {error}") from error
        first_metrics[stem.lower()]["mp4_validation"] = validation
        processed_sources[stem.lower()] = destination

    entries: list[dict[str, Any]] = []
    metrics_videos: list[dict[str, Any]] = []
    # Retain the current seven-video order, then append the first-round additions.
    selected = list(SECOND_ROUND) + list(FIRST_ROUND)
    for stem in selected:
        source = sources[stem]
        metric = metrics_by_stem[stem.lower()]
        metadata = metadata_by_stem[stem.lower()]
        original_path = staged_originals / source.name
        shutil.copy2(source, original_path)
        processed_path = processed_sources[stem.lower()]
        if not processed_path.is_file():
            raise FileNotFoundError(f"MP4 processado ausente para {stem}: {processed_path}")
        observation = SECOND_ROUND_OBSERVATIONS[stem] if stem in SECOND_ROUND_OBSERVATIONS else FIRST_ROUND_OBSERVATION
        relative_original = (release_relative / "originals" / source.name).as_posix()
        relative_processed = (release_relative / "processed" / f"{stem}.mp4").as_posix()
        entries.append(make_manifest_entry(
            stem, observation, metadata, metric, relative_original, relative_processed
        ))
        metrics_videos.append({
            "name": stem,
            "inference": {"model": str(MODEL_PATH), "device": DEVICE,
                          "confidence_threshold": CONFIDENCE, "imgsz": IMAGE_SIZE},
            "quantidade_quadros": int(metric["quantidade_quadros"]),
            "quadros_com_deteccao": int(metric["quadros_com_deteccao"]),
            "percentual_quadros_com_deteccao": float(metric["percentual_quadros_com_deteccao"]),
            "maior_confianca": metric.get("maior_confianca"),
            "mp4_validation": metric.get("mp4_validation"),
        })

    inference_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": str(MODEL_PATH),
        "parameters": {"device": DEVICE, "conf": CONFIDENCE, "imgsz": IMAGE_SIZE},
        "videos": metrics_videos,
    }
    (staging_dir / "metrics.json").write_text(
        json.dumps(inference_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Ensure every staged source and MP4 is readable before publishing the release.
    for entry in entries:
        for key in ("original_video", "processed_video"):
            staged_relative = Path(*Path(entry[key]).parts[2:])
            staged_path = staging_dir / staged_relative
            if not staged_path.is_file() or staged_path.stat().st_size == 0:
                raise RuntimeError(f"Arquivo ausente/vazio antes da publicação: {staged_path}")

    old_manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(old_manifest, dict) or not isinstance(old_manifest.get("videos"), list):
        raise ValueError("gallery.json atual não tem o formato esperado; manifesto não atualizado.")
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_count": len(entries),
        "processed_video_format": "H.264 MP4",
        "videos": entries,
    }

    (GALLERY_DIR / "releases").mkdir(exist_ok=True)
    staging_dir.rename(release_dir)
    backup_path = free_backup_path(tag)
    shutil.copy2(CURRENT_MANIFEST, backup_path)
    temporary_manifest = GALLERY_DIR / f".gallery_{tag}.tmp"
    try:
        temporary_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary_manifest, CURRENT_MANIFEST)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        raise

    print("\nGaleria publicada após validar os dez MP4.")
    print(f"Manifesto: {CURRENT_MANIFEST}")
    print(f"Backup preservado: {backup_path}")
    print(f"Release: {release_dir}")
    print(f"Métricas com configuração: {release_dir / 'metrics.json'}")
    print(f"Vídeos no manifesto: {len(entries)}")


if __name__ == "__main__":
    main()
