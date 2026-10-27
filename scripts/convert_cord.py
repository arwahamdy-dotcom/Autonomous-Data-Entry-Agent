"""
Convert CORD-v2 (Consolidated Receipt Dataset) from Hugging Face to JSONL contract.

CORD provides:
  - image: PIL Image
  - ground_truth: JSON string with menu, sub_total, total, etc.

Usage:
    python scripts/convert_cord.py

Produces:
    data/processed/cord.jsonl
    data/processed/images/cord_<split>_<index>.jpg
"""

import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    make_record, write_jsonl, convert_image_to_rgb_jpeg,
    IMAGE_DIR, REVIEW_DIR,
)


def extract_cord_fields(gt_json_str: str) -> dict:
    """Extract supplier, date, total, invoice_number from CORD ground truth."""
    fields = {
        "invoice_number": "",
        "date": "",
        "supplier": "",
        "total": "",
    }
    if not gt_json_str:
        return fields

    try:
        gt = json.loads(gt_json_str) if isinstance(gt_json_str, str) else gt_json_str
    except Exception:
        return fields

    valid_lines = gt.get("valid_line", [])
    for line in valid_lines:
        category = line.get("category", "")
        words = line.get("words", [])
        text = " ".join(w.get("text", "") for w in words).strip()

        if not text:
            continue

        if "total.total_price" in category or category == "total":
            if not fields["total"]:
                fields["total"] = text
        elif "store_name" in category or "sub_total.store" in category or category == "menu.nm":
            if not fields["supplier"]:
                fields["supplier"] = text
        elif "date" in category:
            if not fields["date"]:
                fields["date"] = text

    return fields


def convert_cord():
    print("=" * 60)
    print("Converting CORD-v2 Dataset from Hugging Face")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  [ERROR] 'datasets' library is required. Run: pip install datasets")
        return

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    out_jsonl = Path("data/processed/cord.jsonl")

    records = []
    try:
        print("  Loading naver-clova-ix/cord-v2...")
        ds = load_dataset("naver-clova-ix/cord-v2", trust_remote_code=True)
    except Exception as e:
        print(f"  [WARN] Failed to load cord-v2: {e}")
        return

    for split in ["train", "validation", "test"]:
        if split not in ds:
            continue
        print(f"  Processing {split} split ({len(ds[split])} records)...")
        for i, item in enumerate(ds[split]):
            doc_id = f"cord_{split}_{i:05d}"
            img_filename = f"{doc_id}.jpg"
            img_path = IMAGE_DIR / img_filename

            # Save image
            pil_img = item.get("image")
            if pil_img and not img_path.exists():
                try:
                    pil_img = pil_img.convert("RGB")
                    pil_img.save(str(img_path), "JPEG", quality=90)
                except Exception as e:
                    print(f"  [WARN] Failed to save image for {doc_id}: {e}")
                    continue

            gt_raw = item.get("ground_truth", "")
            fields = extract_cord_fields(gt_raw)

            record = make_record(
                doc_id=doc_id,
                image_rel_path=f"data/processed/images/{img_filename}",
                language="en",
                source="cord",
                quality="clear",
                ground_truth=fields,
                annotations={"cord_split": split},
                source_split=split,
                source_key=str(i),
            )
            records.append(record)

    if records:
        write_jsonl(records, out_jsonl)
        print(f"\n✅ Converted {len(records)} CORD records -> {out_jsonl}")
    else:
        print("  [WARN] No CORD records converted.")


if __name__ == "__main__":
    convert_cord()
