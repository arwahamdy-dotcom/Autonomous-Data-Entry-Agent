import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image
from datasets import load_dataset

SPLITS = ["train", "val", "test"]
HOLDOUT_TEMPLATES = {"ar_commercial", "mixed_bilingual"}


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def get_cord_total(row, ds):
    split = row["source_split"]
    index = int(row["source_key"])

    if split not in ds or not 0 <= index < len(ds[split]):
        raise ValueError(f"Invalid CORD mapping: {row['doc_id']}")

    gt = json.loads(ds[split][index]["ground_truth"])

    if int(gt["meta"]["image_id"]) != index:
        raise ValueError(f"HF image ID mismatch: {row['doc_id']}")

    total = gt.get("gt_parse", {}).get("total", {}).get("total_price")

    if total is None or not str(total).strip():
        return None

    total = str(total).strip()
    total = re.sub(
        r"^\s*(?:GRAND\s+)?TOTAL\b\s*[:\-]?\s*",
        "",
        total,
        flags=re.IGNORECASE,
    )
    return total if total else None


def patch_rows(rows, ds, root, stats):
    patched = []

    for original in rows:
        row = dict(original)
        annotations = dict(row.get("annotations") or {})
        row["annotations"] = annotations

        if row.get("source") == "cord":
            total = get_cord_total(row, ds)

            if total is None:
                stats["cord_dropped_no_total"] += 1
                continue

            row["ground_truth"] = {
                "invoice_number": "",
                "date": "",
                "supplier": "",
                "total": total,
            }
            row["quality"] = "unassessed"
            annotations["origin_language"] = "id"
            annotations["label_version"] = "v1.1"
            stats["cord_patched"] += 1

        elif row.get("source") == "synthetic":
            template = annotations.get("template_id")

            if template in HOLDOUT_TEMPLATES:
                annotations["holdout_template"] = True
                stats["holdout_tagged"] += 1

        gt = row.get("ground_truth") or {}

        if not any(str(v).strip() for v in gt.values() if v is not None):
            stats["empty_gt_dropped"] += 1
            continue

        image_path = root / row["image_path"]

        if not image_path.is_file():
            raise FileNotFoundError(f"Missing image: {image_path}")

        with Image.open(image_path) as image:
            annotations["image_width"] = image.width
            annotations["image_height"] = image.height

        patched.append(row)

    return patched


def write_jsonl(path, rows):
    backup = path.with_name(path.name + ".v1_0.bak")

    if not backup.exists():
        backup.write_bytes(path.read_bytes())

    temp = path.with_suffix(path.suffix + ".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    temp.replace(path)


def write_split_report(root):
    report_path = root / "data" / "splits" / "split_report.csv"
    backup = report_path.with_name(report_path.name + ".v1_0.bak")

    if report_path.exists() and not backup.exists():
        backup.write_bytes(report_path.read_bytes())

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "source", "language", "quality", "records"])

        for split in SPLITS:
            rows = load_jsonl(root / "data" / "splits" / f"{split}.jsonl")
            counts = Counter(
                (
                    row.get("source", "unknown"),
                    row.get("language", "unknown"),
                    row.get("quality", "unknown"),
                )
                for row in rows
            )

            for (source, language, quality), count in sorted(counts.items()):
                writer.writerow([split, source, language, quality, count])


def main():
    parser = argparse.ArgumentParser(
        description="Apply the OCR dataset v1.1 patch."
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Dataset root containing data/splits and ocr_output.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, only preview.",
    )
    args = parser.parse_args()

    root = args.root.resolve()

    print("Dataset root:", root)

    print("Loading CORD labels...")
    ds = load_dataset("naver-clova-ix/cord-v2")

    stats = Counter()
    planned = {}
    original_ids = {}

    for folder, suffix in [
        ("data/splits", ".jsonl"),
        ("ocr_output", "_with_ocr.jsonl"),
    ]:
        for split in SPLITS:
            path = root / folder / f"{split}{suffix}"

            if not path.is_file():
                raise FileNotFoundError(path)

            rows = load_jsonl(path)
            original_ids[str(path)] = [row["doc_id"] for row in rows]
            planned[str(path)] = patch_rows(rows, ds, root, stats)

    for split in SPLITS:
        split_path = str(root / "data/splits" / f"{split}.jsonl")
        ocr_path = str(root / "ocr_output" / f"{split}_with_ocr.jsonl")

        if original_ids[split_path] != original_ids[ocr_path]:
            raise ValueError(f"Original split/OCR ID mismatch: {split}")

        split_new = [row["doc_id"] for row in planned[split_path]]
        ocr_new = [row["doc_id"] for row in planned[ocr_path]]

        if split_new != ocr_new:
            raise ValueError(f"Patched split/OCR ID mismatch: {split}")

    print("Preflight passed.")
    print("Statistics:", dict(stats))
    print("Files to update:", len(planned))

    if not args.apply:
        print("PREVIEW ONLY — no files were changed.")
        return

    for path_string, rows in planned.items():
        write_jsonl(Path(path_string), rows)

    write_split_report(root)
    print("Patch completed successfully.")


if __name__ == "__main__":
    main()
