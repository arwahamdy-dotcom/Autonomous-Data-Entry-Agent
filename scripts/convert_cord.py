"""
Convert CORD-v2 from Hugging Face into the project JSONL contract.

Preserves original HF split and row index for reproducible v1.1 patching.
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils import make_record, write_jsonl, IMAGE_DIR


def extract_cord_total(gt_json):
    """Extract only gt_parse.total.total_price."""
    if isinstance(gt_json, str):
        gt_json = json.loads(gt_json)

    total = (
        gt_json.get("gt_parse", {})
        .get("total", {})
        .get("total_price")
    )

    if total is None or not str(total).strip():
        return ""

    total = str(total).strip()
    total = re.sub(
        r"^\s*(?:GRAND\s+)?TOTAL\b\s*[:\-]?\s*",
        "",
        total,
        flags=re.IGNORECASE,
    )
    return total


def convert_cord():
    from datasets import load_dataset

    print("Loading naver-clova-ix/cord-v2...")
    ds = load_dataset("naver-clova-ix/cord-v2")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROJECT_ROOT / "data" / "processed" / "cord.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    stats = Counter()

    for split in ["train", "validation", "test"]:
        if split not in ds:
            continue

        print(f"Processing {split}: {len(ds[split])} records")

        for index, item in enumerate(ds[split]):
            doc_id = f"cord_{split}_{index:05d}"
            filename = f"{doc_id}.jpg"
            image_path = IMAGE_DIR / filename

            image = item.get("image")
            if image is None:
                raise ValueError(f"Missing image: {doc_id}")

            rgb_image = image.convert("RGB")
            image_width, image_height = rgb_image.size
            rgb_image.save(image_path, format="JPEG", quality=90)

            gt_raw = item.get("ground_truth", "")
            gt_json = json.loads(gt_raw) if isinstance(gt_raw, str) else gt_raw

            hf_image_id = int(gt_json["meta"]["image_id"])
            if hf_image_id != index:
                raise ValueError(
                    f"HF image ID mismatch for {doc_id}: "
                    f"expected {index}, got {hf_image_id}"
                )

            total = extract_cord_total(gt_json)

            if not total:
                stats["missing_total"] += 1

            record = make_record(
                doc_id=doc_id,
                image_rel_path=f"data/processed/images/{filename}",
                language="en",
                source="cord",
                quality="unassessed",
                ground_truth={
                    "invoice_number": "",
                    "date": "",
                    "supplier": "",
                    "total": total,
                },
                annotations={
                    "cord_split": split,
                    "image_width": image_width,
                    "image_height": image_height,
                },
                source_split=split,
                source_key=str(index),
            )

            records.append(record)
            stats["converted"] += 1

    write_jsonl(records, output_path)

    print("\nConversion complete.")
    print("Statistics:", dict(stats))
    print("Output:", output_path)


if __name__ == "__main__":
    convert_cord()
