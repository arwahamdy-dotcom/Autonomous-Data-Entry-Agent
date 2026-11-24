"""
Shared utilities for the data-entry-ds pipeline.

All scripts import from here for common functions:
- Language detection
- JSONL I/O
- Image conversion
- Contract validation helpers
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────
# Constants (from data_contract.md)
# ──────────────────────────────────────────────

SEED = 42

ALLOWED_LANGUAGES = {"en", "ar", "mixed"}
ALLOWED_SOURCES = {"sroie", "cord", "coru", "invoices_hf", "synthetic", "real"}
ALLOWED_QUALITIES = {"clear", "blurry", "tilted", "noisy", "unassessed"}
GROUND_TRUTH_KEYS = {"invoice_number", "date", "supplier", "total"}

IMAGE_DIR = Path("data/processed/images")
REVIEW_DIR = Path("data/review")
SPLITS_DIR = Path("data/splits")
SYNTH_OUT_DIR = Path("data/synth/out")

# ──────────────────────────────────────────────
# Language Detection
# ──────────────────────────────────────────────

def detect_lang(text: str) -> str:
    """Detect language from text content.
    
    Returns 'ar', 'en', or 'mixed' based on character analysis.
    Defaults to 'en' if no Arabic or Latin characters are found.
    """
    if not text or not text.strip():
        return "en"
    ar = bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text))
    en = bool(re.search(r'[A-Za-z]', text))
    if ar and en:
        return "mixed"
    elif ar:
        return "ar"
    else:
        return "en"


# ──────────────────────────────────────────────
# JSONL I/O
# ──────────────────────────────────────────────

def read_jsonl(path: str | Path) -> list[dict]:
    """Read a JSONL file and return a list of dicts."""
    path = Path(path)
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSON at {path}:{line_num}: {e}")
    return records


def write_jsonl(records: list[dict], path: str | Path, overwrite: bool = True):
    """Write a list of dicts to a JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "a"
    with open(path, mode, encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(records)} records to {path}")


# ──────────────────────────────────────────────
# Contract Helpers
# ──────────────────────────────────────────────

def make_record(
    doc_id: str,
    source: str,
    language: str,
    ground_truth: dict,
    source_split: str = "",
    source_key: str = "",
    quality: str = "unassessed",
    annotations: Optional[dict] = None,
    image_rel_path: Optional[str] = None,
    **kwargs,
) -> dict:
    """Create a record conforming to the data contract.
    
    Ensures all required fields are present and ground_truth
    has exactly the four required keys with string values.
    """
    # Ensure ground_truth has exactly the right keys, all strings
    gt = {}
    for key in GROUND_TRUTH_KEYS:
        val = ground_truth.get(key, "")
        # Convert None, lists, dicts, numbers to string safely
        if val is None:
            val = ""
        elif not isinstance(val, str):
            val = str(val)
        # Trim leading/trailing whitespace
        gt[key] = val.strip()

    assert language in ALLOWED_LANGUAGES, f"Invalid language: {language}"
    assert source in ALLOWED_SOURCES, f"Invalid source: {source}"
    assert quality in ALLOWED_QUALITIES, f"Invalid quality: {quality}"

    image_path = str(image_rel_path) if image_rel_path else str(IMAGE_DIR / f"{doc_id}.jpg")

    return {
        "doc_id": doc_id,
        "image_path": image_path,
        "language": language,
        "source": source,
        "quality": quality,
        "ground_truth": gt,
        "ocr": {"engine": "", "words": []},
        "prediction": {},
        "annotations": annotations or {},
        "source_split": source_split,
        "source_key": source_key,
    }


# ──────────────────────────────────────────────
# Image Utilities
# ──────────────────────────────────────────────

def convert_image_to_rgb_jpeg(
    input_path: str | Path,
    output_path: str | Path,
    quality: int = 95,
):
    """Convert an image to RGB JPEG format.
    
    Args:
        input_path: Source image path (any format PIL supports).
        output_path: Destination path (should end in .jpg).
        quality: JPEG quality (1-100).
    """
    from PIL import Image

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(input_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(str(output_path), "JPEG", quality=quality)


def compute_image_md5(path: str | Path) -> str:
    """Compute MD5 hash of an image file for deduplication."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────
# Validation Helpers
# ──────────────────────────────────────────────

def validate_record(record: dict, check_image: bool = True) -> list[str]:
    """Validate a record against the v1.1 data contract.

    The contract permits empty ground-truth strings and preserves localized
    date/amount display strings, so this function validates their types and
    shape but does not impose a single date or currency format.
    """
    if not isinstance(record, dict):
        return [f"Record must be a JSON object, got {type(record).__name__}"]

    errors = []
    required_keys = (
        "doc_id", "image_path", "language", "source", "quality",
        "ground_truth", "ocr", "prediction", "annotations",
        "source_split", "source_key",
    )
    for key in required_keys:
        if key not in record:
            errors.append(f"Missing required key: {key}")

    for key in ("doc_id", "image_path", "source_split", "source_key"):
        if key in record and not isinstance(record[key], str):
            errors.append(f"{key} must be string, got {type(record[key]).__name__}")
    if isinstance(record.get("doc_id"), str) and not record["doc_id"].strip():
        errors.append("doc_id must not be empty")
    for key, allowed in (("language", ALLOWED_LANGUAGES),
                         ("source", ALLOWED_SOURCES),
                         ("quality", ALLOWED_QUALITIES)):
        if key in record:
            value = record[key]
            if not isinstance(value, str) or value not in allowed:
                errors.append(f"Invalid {key}: {value}")

    for key in ("ocr", "prediction", "annotations"):
        if key in record and not isinstance(record[key], dict):
            errors.append(f"{key} must be a dict, got {type(record[key]).__name__}")

    gt = record.get("ground_truth")
    if not isinstance(gt, dict):
        if "ground_truth" in record:
            errors.append(f"ground_truth must be a dict, got {type(gt).__name__}")
    else:
        gt_keys = set(gt)
        if gt_keys != GROUND_TRUTH_KEYS:
            missing = GROUND_TRUTH_KEYS - gt_keys
            extra = gt_keys - GROUND_TRUTH_KEYS
            if missing:
                errors.append(f"ground_truth missing keys: {sorted(missing)}")
            if extra:
                errors.append(f"ground_truth has extra keys: {sorted(extra)}")
        for key, value in gt.items():
            if not isinstance(value, str):
                errors.append(f"ground_truth.{key} must be string, got {type(value).__name__}")

    ocr = record.get("ocr")
    if isinstance(ocr, dict):
        if "engine" not in ocr:
            errors.append("Missing required key: ocr.engine")
        elif not isinstance(ocr["engine"], str):
            errors.append("ocr.engine must be string")
        if "words" not in ocr:
            errors.append("Missing required key: ocr.words")
        elif not isinstance(ocr["words"], list):
            errors.append("ocr.words must be a list")

    annotations = record.get("annotations")
    if isinstance(annotations, dict):
        for key in ("image_width", "image_height"):
            value = annotations.get(key)
            if key not in annotations:
                errors.append(f"Missing required key: annotations.{key}")
            elif isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                errors.append(f"annotations.{key} must be a positive integer")
        label_version = annotations.get("label_version")
        # The v1.1 patch added this marker to patched CORD records. Original
        # synthetic records predate that patch and omit it in the frozen ZIP.
        if record.get("source") == "cord" and "label_version" not in annotations:
            errors.append("Missing required key: annotations.label_version")
        elif "label_version" in annotations and (not isinstance(label_version, str) or label_version != "v1.1"):
            errors.append("annotations.label_version must be 'v1.1'")

    image_value = record.get("image_path")
    if isinstance(image_value, str):
        if not image_value.strip():
            errors.append("image_path must not be empty")
        else:
            img_path = Path(image_value)
            path_parts = image_value.replace("\\", "/").split("/")
            if img_path.is_absolute() or image_value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[/\\]", image_value):
                errors.append(f"Invalid image_path (must be relative): {image_value}")
            elif ".." in path_parts:
                errors.append(f"Invalid image_path (parent traversal): {image_value}")
            elif check_image:
                if not img_path.is_file():
                    errors.append(f"Image not found: {image_value}")
                else:
                    try:
                        from PIL import Image
                        with Image.open(img_path) as image:
                            image.verify()
                    except Exception as exc:
                        errors.append(f"Image is not readable: {image_value} ({type(exc).__name__}: {exc})")

    return errors
