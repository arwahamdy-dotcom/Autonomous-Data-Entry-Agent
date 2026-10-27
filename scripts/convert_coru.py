"""
Convert CORU (ReceiptSense) dataset to the shared JSONL contract.

CORU provides:
  - Arabic/English/Mixed receipts
  - Potentially: merchant, date, receipt number, total
  - May only have bounding boxes (detection) without text values

IMPORTANT: Run Phase A verification FIRST before full conversion.
    - Check license
    - Check annotation format
    - Decide if annotations have text values or only bounding boxes

Usage (from Colab):
    # Step 1: Verify the dataset first
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/convert_coru.py --verify-only

    # Step 2: Full conversion (after verification)
    !python scripts/convert_coru.py

    # Step 3: Convert with sampling (for large datasets)
    !python scripts/convert_coru.py --sample 3000

Produces:
    data/processed/coru.jsonl
    data/processed/images/coru_<split>_<key>.jpg
    data/review/coru_review.jsonl
"""

import sys
import json
import argparse
import random
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    detect_lang, make_record, write_jsonl, convert_image_to_rgb_jpeg,
    IMAGE_DIR, REVIEW_DIR, SEED,
)


def verify_coru():
    """Phase A: Verify CORU dataset before downloading everything.
    
    Lists files, checks sizes, inspects annotation format.
    """
    print("=" * 60)
    print("CORU Dataset Verification (Phase A)")
    print("=" * 60)

    try:
        from huggingface_hub import list_repo_files, hf_hub_url, HfApi
    except ImportError:
        print("  [ERROR] huggingface_hub not installed.")
        print("  Run: pip install huggingface_hub")
        return

    repo_id = "abdoelsayed/CORU"
    print(f"\n  Listing files in: {repo_id}")

    try:
        files = list_repo_files(repo_id, repo_type="dataset")
        print(f"  Total files: {len(files)}")
        print(f"\n  First 80 files:")
        for f in files[:80]:
            print(f"    {f}")

        # Categorize files
        extensions = Counter()
        for f in files:
            ext = Path(f).suffix.lower()
            extensions[ext] += 1

        print(f"\n  File type distribution:")
        for ext, count in extensions.most_common():
            print(f"    {ext}: {count}")

        # Check for annotation files
        ann_files = [f for f in files if any(
            kw in f.lower() for kw in ["annotation", "label", "json", "csv", "txt", "ground"]
        )]
        print(f"\n  Potential annotation files ({len(ann_files)}):")
        for f in ann_files[:30]:
            print(f"    {f}")

    except Exception as e:
        print(f"  [ERROR] Failed to list repo: {e}")
        return

    # Check dataset card for license
    try:
        api = HfApi()
        info = api.dataset_info(repo_id)
        print(f"\n  Dataset card info:")
        print(f"    License: {getattr(info, 'license', 'NOT SPECIFIED')}")
        print(f"    Tags: {getattr(info, 'tags', [])}")
        print(f"    Downloads: {getattr(info, 'downloads', 'N/A')}")
    except Exception as e:
        print(f"  [WARN] Could not get dataset info: {e}")

    print("\n  ⚠️  NEXT STEPS:")
    print("  1. Check the license — record in docs/datasets_licenses.md")
    print("  2. Download ONE annotation file and inspect the format")
    print("  3. Determine if annotations have TEXT VALUES or only BOUNDING BOXES")
    print("  4. If text values → run full conversion")
    print("  5. If only boxes → use for OCR benchmarking, not field extraction")


def convert_coru(sample_size: int = 0):
    """Main conversion logic for CORU dataset.
    
    Args:
        sample_size: If > 0, take a language-balanced random sample.
                     Recommended: 3000 for full pipeline.
    """
    print("=" * 60)
    print("Converting CORU dataset")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  [ERROR] 'datasets' library not installed.")
        sys.exit(1)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Load CORU
    print("  Loading CORU from HuggingFace...")
    try:
        ds = load_dataset("abdoelsayed/CORU")
    except Exception as e:
        print(f"  [ERROR] Failed to load CORU: {e}")
        print("  Try loading a specific config:")
        print("    ds = load_dataset('abdoelsayed/CORU', 'receipt_detection')")
        sys.exit(1)

    records = []
    review_records = []
    stats = Counter()

    for split_name in ds.keys():
        split_data = ds[split_name]
        print(f"  Processing split '{split_name}': {len(split_data)} documents")

        for idx, sample in enumerate(split_data):
            source_key = str(sample.get("id", f"{idx:05d}"))
            doc_id = f"coru_{split_name}_{source_key}"

            # ── Extract ground truth ──
            # CORU format varies — adapt based on Phase A verification.
            # This is a best-effort extraction; adjust field names after
            # inspecting the actual annotation format.
            ground_truth = {
                "invoice_number": "",
                "date": "",
                "supplier": "",
                "total": "",
            }
            annotations_raw = {}
            needs_review = False
            review_reasons = []

            # Try common field name patterns
            for field_map in [
                # (our_field, possible_coru_keys)
                ("supplier", ["merchant", "merchant_name", "store_name", "company", "supplier"]),
                ("date", ["date", "transaction_date", "receipt_date"]),
                ("total", ["total", "total_amount", "grand_total", "amount"]),
                ("invoice_number", ["receipt_number", "receipt_no", "invoice_number", "transaction_id"]),
            ]:
                our_key, candidates = field_map
                for cand in candidates:
                    val = sample.get(cand)
                    if val is not None and val != "":
                        if not isinstance(val, str):
                            val = str(val)
                        ground_truth[our_key] = val.strip()
                        annotations_raw[cand] = val
                        break

            # Try nested annotations
            for ann_key in ["annotations", "annotation", "label", "labels", "ground_truth"]:
                ann = sample.get(ann_key)
                if isinstance(ann, dict):
                    annotations_raw[ann_key] = ann
                    for field_map in [
                        ("supplier", ["merchant", "merchant_name", "store_name"]),
                        ("date", ["date", "transaction_date"]),
                        ("total", ["total", "total_amount"]),
                        ("invoice_number", ["receipt_number", "receipt_no"]),
                    ]:
                        our_key, candidates = field_map
                        if not ground_truth[our_key]:
                            for cand in candidates:
                                val = ann.get(cand)
                                if val is not None and val != "":
                                    ground_truth[our_key] = str(val).strip()
                                    break
                elif isinstance(ann, str):
                    try:
                        ann_dict = json.loads(ann)
                        annotations_raw[ann_key] = ann_dict
                    except (json.JSONDecodeError, TypeError):
                        annotations_raw[ann_key] = ann

            # Detect language from extracted text + any OCR text
            text_parts = [v for v in ground_truth.values() if v]
            ocr_text = sample.get("text", sample.get("ocr_text", ""))
            if ocr_text:
                text_parts.append(str(ocr_text))
            all_text = " ".join(text_parts)
            language = detect_lang(all_text)

            # Flag for review if we got nothing useful
            non_empty = sum(1 for v in ground_truth.values() if v)
            if non_empty == 0:
                needs_review = True
                review_reasons.append("no_fields_extracted")

            annotations = {
                "origin_dataset": "coru",
                "original_fields": annotations_raw,
            }

            # Save image
            output_img = IMAGE_DIR / f"{doc_id}.jpg"
            try:
                image = sample.get("image")
                if image is not None:
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    image.save(str(output_img), "JPEG", quality=95)
                else:
                    needs_review = True
                    review_reasons.append("no_image")
                    continue
            except Exception as e:
                print(f"  [WARN] Failed to save image for {doc_id}: {e}")
                continue

            record = make_record(
                doc_id=doc_id,
                source="coru",
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

    # Language-balanced sampling (if requested)
    if sample_size > 0 and len(records) > sample_size:
        print(f"\n  Sampling {sample_size} records (language-balanced)...")
        random.seed(SEED)

        by_lang = {"ar": [], "en": [], "mixed": []}
        for r in records:
            lang = r["language"]
            if lang in by_lang:
                by_lang[lang].append(r)

        # Target: proportional to original, but ensure minority languages
        total = sum(len(v) for v in by_lang.values())
        sampled = []
        for lang, lang_records in by_lang.items():
            proportion = len(lang_records) / total if total > 0 else 0
            n = max(int(sample_size * proportion), min(100, len(lang_records)))
            n = min(n, len(lang_records))
            random.shuffle(lang_records)
            sampled.extend(lang_records[:n])

        # Fill remaining quota
        remaining = sample_size - len(sampled)
        if remaining > 0:
            sampled_ids = {r["doc_id"] for r in sampled}
            extras = [r for r in records if r["doc_id"] not in sampled_ids]
            random.shuffle(extras)
            sampled.extend(extras[:remaining])

        records = sampled[:sample_size]
        print(f"  Sampled {len(records)} records")

    # Write outputs
    output_path = Path("data/processed/coru.jsonl")
    write_jsonl(records, output_path)

    if review_records:
        review_path = REVIEW_DIR / "coru_review.jsonl"
        write_jsonl(review_records, review_path)

    # Summary
    print(f"\n  CORU Conversion Summary:")
    print(f"  Total records: {len(records)}")
    print(f"  Records needing review: {len(review_records)}")
    for key, count in sorted(stats.items()):
        print(f"    {key}: {count}")

    for field in ["invoice_number", "date", "supplier", "total"]:
        empty = sum(1 for r in records if not r["ground_truth"][field])
        print(f"  Empty '{field}': {empty}/{len(records)}")

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CORU dataset")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify the dataset (Phase A)")
    parser.add_argument("--sample", type=int, default=0,
                        help="Language-balanced sample size (0 = all)")
    args = parser.parse_args()

    if args.verify_only:
        verify_coru()
    else:
        convert_coru(sample_size=args.sample)
