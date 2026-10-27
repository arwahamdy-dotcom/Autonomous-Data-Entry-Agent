"""
Check for data leakage across splits.

Checks:
  1. No doc_id appears in more than one split
  2. No duplicate image content across splits (MD5 hash)
  3. Synthetic holdout templates appear only in the test split

Usage (from Colab):
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/check_leakage.py

    # Check specific split files
    !python scripts/check_leakage.py --splits data/splits/train.jsonl data/splits/val.jsonl data/splits/test.jsonl

Exit codes:
    0 = no leakage
    1 = leakage detected
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import read_jsonl, compute_image_md5, SPLITS_DIR


def check_leakage(split_files: list[str] = None):
    """Check for data leakage across all split files.
    
    Args:
        split_files: List of JSONL file paths. If None, auto-discovers
                     files in data/splits/.
    """
    print("=" * 60)
    print("DATA LEAKAGE CHECK")
    print("=" * 60)

    # Auto-discover split files if not specified
    if not split_files:
        split_files = sorted(str(f) for f in SPLITS_DIR.glob("*.jsonl"))

    if not split_files:
        print("  ❌ No split files found in data/splits/")
        print("  Run create_splits.py first, or specify files with --splits")
        sys.exit(1)

    print(f"  Checking {len(split_files)} split files:")
    for f in split_files:
        print(f"    {f}")

    errors = []
    warnings = []

    # ────────────────────────────────────────────
    # Check 1: doc_id uniqueness across splits
    # ────────────────────────────────────────────
    print(f"\n  --- Check 1: doc_id uniqueness across splits ---")
    
    id_to_splits = defaultdict(list)  # doc_id → [split_file, ...]
    split_records = {}  # split_file → [records]

    for filepath in split_files:
        split_name = Path(filepath).stem
        records = read_jsonl(filepath)
        split_records[filepath] = records
        print(f"    {split_name}: {len(records)} records")

        for record in records:
            doc_id = record.get("doc_id", "")
            if doc_id:
                id_to_splits[doc_id].append(split_name)

    leaked_ids = {
        doc_id: splits
        for doc_id, splits in id_to_splits.items()
        if len(splits) > 1
    }

    if leaked_ids:
        errors.append(f"doc_id leakage: {len(leaked_ids)} documents appear in multiple splits")
        for doc_id, splits in list(leaked_ids.items())[:20]:
            errors.append(f"  '{doc_id}' in: {splits}")
        if len(leaked_ids) > 20:
            errors.append(f"  ... and {len(leaked_ids) - 20} more")
        print(f"  ❌ {len(leaked_ids)} leaked doc_ids found!")
    else:
        print(f"  ✅ No doc_id leakage")

    # ────────────────────────────────────────────
    # Check 2: Image content deduplication (MD5)
    # ────────────────────────────────────────────
    print(f"\n  --- Check 2: Image content deduplication (MD5) ---")
    
    hash_to_splits = defaultdict(list)  # md5 → [(split, doc_id), ...]
    images_checked = 0
    images_missing = 0

    for filepath in split_files:
        split_name = Path(filepath).stem
        for record in split_records[filepath]:
            img_path = Path(record.get("image_path", ""))
            doc_id = record.get("doc_id", "")

            if img_path.exists():
                md5 = compute_image_md5(img_path)
                hash_to_splits[md5].append((split_name, doc_id))
                images_checked += 1
            else:
                images_missing += 1

    duplicate_images = {
        md5: entries
        for md5, entries in hash_to_splits.items()
        if len(entries) > 1
    }

    # Filter: only flag cross-split duplicates (same-split dupes are a different issue)
    cross_split_dupes = {}
    for md5, entries in duplicate_images.items():
        splits_involved = set(s for s, _ in entries)
        if len(splits_involved) > 1:
            cross_split_dupes[md5] = entries

    if cross_split_dupes:
        errors.append(f"Image content leakage: {len(cross_split_dupes)} images have identical content across splits")
        for md5, entries in list(cross_split_dupes.items())[:10]:
            errors.append(f"  MD5={md5[:12]}... in: {entries}")
        print(f"  ❌ {len(cross_split_dupes)} cross-split duplicate images found!")
    else:
        print(f"  ✅ No cross-split image duplicates")

    print(f"  Images checked: {images_checked}, missing: {images_missing}")

    if images_missing > 0:
        warnings.append(f"{images_missing} images could not be found (skipped MD5 check)")

    # Same-split duplicates (warning, not error)
    same_split_dupes = {
        md5: entries
        for md5, entries in duplicate_images.items()
        if md5 not in cross_split_dupes
    }
    if same_split_dupes:
        warnings.append(f"{len(same_split_dupes)} duplicate images within the same split")

    # ────────────────────────────────────────────
    # Check 3: Synthetic template holdout
    # ────────────────────────────────────────────
    print(f"\n  --- Check 3: Synthetic template holdout ---")
    
    template_to_splits = defaultdict(set)  # template_id → {splits}

    for filepath in split_files:
        split_name = Path(filepath).stem
        for record in split_records[filepath]:
            if record.get("source") == "synthetic":
                template_id = record.get("annotations", {}).get("template_id", "")
                if template_id:
                    template_to_splits[template_id].add(split_name)

    if template_to_splits:
        # Check for test-only holdout templates
        test_only_templates = {
            t for t, splits in template_to_splits.items()
            if splits == {"test"} or splits == {"real_test"}
        }

        if test_only_templates:
            print(f"  ✅ Template holdout intact: {len(test_only_templates)} test-only templates reserved for evaluation:")
            for t in sorted(test_only_templates):
                print(f"    - {t}")
        else:
            warnings.append("No test-only synthetic templates found")
            print("  ⚠️ No test-only templates detected")

        print(f"  Total synthetic templates: {len(template_to_splits)}")
        for t, splits in sorted(template_to_splits.items()):
            print(f"    {t}: {splits}")
    else:
        print(f"  ℹ️  No synthetic records found (skipping template check)")

    # ────────────────────────────────────────────
    # Final Summary
    # ────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"LEAKAGE CHECK SUMMARY")
    print(f"{'=' * 60}")

    if warnings:
        print(f"\n  ⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    {w}")

    if errors:
        print(f"\n  ❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    {e}")
        print(f"\n  ❌ LEAKAGE DETECTED — {len(errors)} issues found")
        sys.exit(1)
    else:
        print(f"\n  ✅ NO LEAKAGE DETECTED")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Check for data leakage across splits")
    parser.add_argument("--splits", nargs="+",
                        help="Split JSONL files to check (default: all in data/splits/)")
    parser.add_argument("--splits_dir", type=str, default="data/splits",
                        help="Directory containing split files")
    args, _ = parser.parse_known_args()

    split_files = args.splits
    if not split_files and args.splits_dir:
        dir_p = Path(args.splits_dir)
        split_files = [str(f) for f in sorted(dir_p.glob("*.jsonl"))]

    check_leakage(split_files=split_files)


if __name__ == "__main__":
    main()
