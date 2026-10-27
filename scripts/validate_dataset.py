"""
Validate a JSONL dataset file against the data contract.

Checks:
  - Required keys present
  - language, source, quality in allowed sets
  - Image exists and opens (PIL)
  - doc_id is unique within the file
  - ground_truth has exactly 4 keys, all strings
  - Reports counts of empty fields per field

Usage (from Colab):
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/validate_dataset.py data/processed/sroie.jsonl
    !python scripts/validate_dataset.py data/processed/cord.jsonl
    !python scripts/validate_dataset.py data/splits/train.jsonl --check-images

    # Validate all processed files at once
    !python scripts/validate_dataset.py data/processed/*.jsonl

Exit codes:
    0 = no errors
    1 = errors found
"""

import sys
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import read_jsonl, validate_record, GROUND_TRUTH_KEYS


def validate_file(filepath: str, check_images: bool = False) -> dict:
    """Validate a single JSONL file.
    
    Returns a summary dict with counts and errors.
    """
    filepath = Path(filepath)
    print(f"\n{'=' * 60}")
    print(f"Validating: {filepath}")
    print(f"{'=' * 60}")

    if not filepath.exists():
        print(f"  ❌ File not found: {filepath}")
        return {"file": str(filepath), "error": "file_not_found", "total_errors": 1}

    records = read_jsonl(filepath)
    print(f"  Records: {len(records)}")

    errors = []
    warnings = []
    doc_ids = []
    field_empty_counts = Counter()
    lang_counts = Counter()
    source_counts = Counter()
    quality_counts = Counter()

    for i, record in enumerate(records):
        record_errors = validate_record(record, check_image=check_images)
        if record_errors:
            for err in record_errors:
                errors.append(f"  Record {i} (doc_id={record.get('doc_id', '???')}): {err}")

        # Track doc_ids for uniqueness
        doc_id = record.get("doc_id", "")
        if doc_id:
            doc_ids.append(doc_id)

        # Count empty fields
        gt = record.get("ground_truth", {})
        for field in GROUND_TRUTH_KEYS:
            if not gt.get(field, ""):
                field_empty_counts[field] += 1

        # Distribution counts
        lang_counts[record.get("language", "unknown")] += 1
        source_counts[record.get("source", "unknown")] += 1
        quality_counts[record.get("quality", "unknown")] += 1

    # Check uniqueness
    seen = set()
    duplicates = []
    for doc_id in doc_ids:
        if doc_id in seen:
            duplicates.append(doc_id)
        seen.add(doc_id)

    if duplicates:
        errors.append(f"  Duplicate doc_ids ({len(duplicates)}): {duplicates[:10]}")

    # ── Report ──
    total = len(records)

    print(f"\n  --- Distribution ---")
    print(f"  Languages: {dict(lang_counts.most_common())}")
    print(f"  Sources:   {dict(source_counts.most_common())}")
    print(f"  Quality:   {dict(quality_counts.most_common())}")

    print(f"\n  --- Empty Fields ---")
    for field in sorted(GROUND_TRUTH_KEYS):
        empty = field_empty_counts[field]
        pct = (empty / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        status = "⚠️" if pct > 50 else "✅"
        print(f"  {status} {field:20s}: {empty:5d}/{total} ({pct:5.1f}%) {bar}")

    print(f"\n  --- Unique IDs ---")
    print(f"  Total doc_ids: {len(doc_ids)}")
    print(f"  Unique doc_ids: {len(seen)}")
    print(f"  Duplicates: {len(duplicates)}")

    if errors:
        print(f"\n  ❌ ERRORS ({len(errors)}):")
        for err in errors[:50]:  # Show first 50
            print(f"    {err}")
        if len(errors) > 50:
            print(f"    ... and {len(errors) - 50} more errors")
    else:
        print(f"\n  ✅ No errors found!")

    return {
        "file": str(filepath),
        "total_records": total,
        "total_errors": len(errors),
        "duplicate_ids": len(duplicates),
        "empty_fields": dict(field_empty_counts),
        "languages": dict(lang_counts),
        "sources": dict(source_counts),
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate JSONL dataset files against the data contract"
    )
    parser.add_argument("files", nargs="*", default=None, help="JSONL files to validate")
    parser.add_argument("--input_dir", type=str, default="data/processed", help="Directory containing JSONL files")
    parser.add_argument("--check-images", action="store_true",
                        help="Also verify that image files exist and open")
    args, _ = parser.parse_known_args()

    files = args.files
    if not files:
        input_p = Path(args.input_dir)
        files = [str(f) for f in sorted(input_p.glob("*.jsonl"))]
        if not files:
            # Also check splits
            files = [str(f) for f in sorted(Path("data/splits").glob("*.jsonl"))]

    total_errors = 0
    results = []

    for filepath in files:
        path = Path(filepath)
        if "*" in str(path):
            matched = sorted(path.parent.glob(path.name))
            for m in matched:
                result = validate_file(str(m), check_images=args.check_images)
                results.append(result)
                total_errors += result.get("total_errors", 0)
        else:
            result = validate_file(filepath, check_images=args.check_images)
            results.append(result)
            total_errors += result.get("total_errors", 0)

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Files checked: {len(results)}")
    print(f"  Total errors:  {total_errors}")

    for r in results:
        status = "✅" if r.get("total_errors", 0) == 0 else "❌"
        print(f"  {status} {r['file']}: {r.get('total_records', 0)} records, "
              f"{r.get('total_errors', 0)} errors")

    if total_errors > 0:
        print(f"\n  ❌ VALIDATION FAILED with {total_errors} errors")
        sys.exit(1)
    else:
        print(f"\n  ✅ ALL FILES PASSED VALIDATION")
        sys.exit(0)


if __name__ == "__main__":
    main()
