"""
Convert SROIE (ICDAR 2019) dataset to the shared JSONL contract.

SROIE provides:
  - supplier (company), date, total, address
  - Does NOT have invoice_number

Usage:
    python scripts/convert_sroie.py

Expects:
    data/raw/sroie/  (downloaded dataset)

Produces:
    data/processed/sroie.jsonl
    data/processed/images/sroie_<split>_<key>.jpg
    data/review/sroie_review.jsonl  (suspicious records)
"""

import sys
import json
from pathlib import Path
from collections import Counter

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    detect_lang, make_record, write_jsonl, convert_image_to_rgb_jpeg,
    IMAGE_DIR, REVIEW_DIR,
)


def find_sroie_root() -> Path:
    """Locate the SROIE raw data directory."""
    candidates = [
        Path("data/raw/sroie"),
        Path("data/raw/SROIE"),
        Path("data/raw/ICDAR2019-SROIE"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "SROIE data not found. Expected one of: " + ", ".join(str(c) for c in candidates)
    )


def parse_sroie_annotation(ann_path: Path) -> dict:
    """Parse a SROIE annotation file.
    
    SROIE annotation format (one key-value per line):
        company: SOME COMPANY NAME
        date: 25/10/2024
        address: 123 STREET
        total: 25.50
    """
    fields = {}
    text = ann_path.read_text(encoding="utf-8", errors="replace").strip()
    
    for line in text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            fields[key] = value
    
    return fields


def convert_sroie():
    """Main conversion logic for SROIE dataset."""
    print("=" * 60)
    print("Converting SROIE dataset")
    print("=" * 60)

    root = find_sroie_root()
    print(f"  Found SROIE at: {root}")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    review_records = []
    stats = Counter()

    # SROIE typically has train/ and test/ directories
    # Each contains images (.jpg) and annotations (.txt)
    for split_name in ["train", "test"]:
        split_dir = root / split_name
        if not split_dir.exists():
            # Try flat structure
            split_dir = root
            split_name = "train"  # Default if no split dirs

        # Find image files
        image_files = sorted(
            list(split_dir.glob("*.jpg")) +
            list(split_dir.glob("*.png")) +
            list(split_dir.glob("*.jpeg"))
        )

        # Also check subdirectories (img/ and box/ or entities/)
        for subdir in ["img", "images", "image"]:
            sub = split_dir / subdir
            if sub.exists():
                image_files = sorted(
                    list(sub.glob("*.jpg")) +
                    list(sub.glob("*.png")) +
                    list(sub.glob("*.jpeg"))
                )
                break

        print(f"  Split '{split_name}': found {len(image_files)} images")

        for img_path in image_files:
            source_key = img_path.stem
            doc_id = f"sroie_{split_name}_{source_key}"

            # Find corresponding annotation file
            ann_path = None
            for ann_dir in [split_dir, split_dir / "entities", split_dir / "box", split_dir / "labels"]:
                candidate = ann_dir / f"{source_key}.txt"
                if candidate.exists():
                    ann_path = candidate
                    break

            # Parse annotations
            ground_truth = {
                "invoice_number": "",  # SROIE does not have invoice_number
                "date": "",
                "supplier": "",
                "total": "",
            }

            annotations = {"origin_dataset": "sroie"}
            needs_review = False
            review_reasons = []

            if ann_path:
                parsed = parse_sroie_annotation(ann_path)
                ground_truth["supplier"] = parsed.get("company", "")
                ground_truth["date"] = parsed.get("date", "")
                ground_truth["total"] = parsed.get("total", "")
                
                # Store original annotations
                annotations["original_fields"] = parsed

                # Flag suspicious records
                if not ground_truth["total"]:
                    needs_review = True
                    review_reasons.append("missing_total")
                if not ground_truth["supplier"]:
                    needs_review = True
                    review_reasons.append("missing_supplier")
            else:
                needs_review = True
                review_reasons.append("no_annotation_file")

            # Detect language from all text
            all_text = " ".join(
                v for v in ground_truth.values() if v
            )
            language = detect_lang(all_text)

            # Convert image
            output_img = IMAGE_DIR / f"{doc_id}.jpg"
            try:
                convert_image_to_rgb_jpeg(img_path, output_img)
            except Exception as e:
                print(f"  [WARN] Failed to convert image {img_path}: {e}")
                needs_review = True
                review_reasons.append(f"image_conversion_failed: {e}")
                continue

            # Build record
            record = make_record(
                doc_id=doc_id,
                source="sroie",
                language=language,
                ground_truth=ground_truth,
                source_split=split_name,
                source_key=source_key,
                annotations=annotations,
            )

            records.append(record)
            stats[f"{split_name}_{language}"] += 1

            if needs_review:
                record_copy = record.copy()
                record_copy["annotations"] = {
                    **record_copy["annotations"],
                    "needs_manual_verification": True,
                    "review_reasons": review_reasons,
                }
                review_records.append(record_copy)
                stats["review"] += 1

        if not image_files and split_dir == root:
            break  # Don't try 'test' if we used flat structure

    # Write outputs
    output_path = Path("data/processed/sroie.jsonl")
    write_jsonl(records, output_path)

    if review_records:
        review_path = REVIEW_DIR / "sroie_review.jsonl"
        write_jsonl(review_records, review_path)

    # Summary
    print(f"\n  SROIE Conversion Summary:")
    print(f"  Total records: {len(records)}")
    print(f"  Records needing review: {len(review_records)}")
    for key, count in sorted(stats.items()):
        print(f"    {key}: {count}")

    # Count empty fields
    for field in ["invoice_number", "date", "supplier", "total"]:
        empty = sum(1 for r in records if not r["ground_truth"][field])
        print(f"  Empty '{field}': {empty}/{len(records)}")

    return records


if __name__ == "__main__":
    convert_sroie()
