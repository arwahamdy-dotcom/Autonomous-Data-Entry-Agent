"""
Convert HuggingFace Invoice dataset to the shared JSONL contract.

Candidate: katanaml-org/invoices-donut-data-v1
  - Expected to have invoice_number
  - Verify exact repo name and fields in Phase A

Usage (from Colab):
    # Step 1: Verify first
    %cd /content/drive/MyDrive/data-entry-ds
    !python scripts/convert_invoices.py --verify-only

    # Step 2: Full conversion
    !python scripts/convert_invoices.py

Produces:
    data/processed/invoices.jsonl
    data/processed/images/invoices_hf_<split>_<key>.jpg
    data/review/invoices_review.jsonl
"""

import sys
import json
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    detect_lang, make_record, write_jsonl,
    IMAGE_DIR, REVIEW_DIR,
)


# Candidate repo names to try
CANDIDATE_REPOS = [
    "katanaml-org/invoices-donut-data-v1",
    "katanaml/invoices-donut-data-v1",
    "katanaml-org/invoices-donut-data-v2",
]


def verify_invoices():
    """Phase A: Verify the invoice dataset before full conversion."""
    print("=" * 60)
    print("HF Invoice Dataset Verification (Phase A)")
    print("=" * 60)

    try:
        from huggingface_hub import list_repo_files, HfApi
    except ImportError:
        print("  [ERROR] huggingface_hub not installed.")
        return

    api = HfApi()

    for repo_id in CANDIDATE_REPOS:
        print(f"\n  Trying repo: {repo_id}")
        try:
            files = list_repo_files(repo_id, repo_type="dataset")
            print(f"  ✅ Found! Total files: {len(files)}")

            print(f"\n  First 50 files:")
            for f in files[:50]:
                print(f"    {f}")

            extensions = Counter()
            for f in files:
                ext = Path(f).suffix.lower()
                extensions[ext] += 1
            print(f"\n  File types: {dict(extensions.most_common())}")

            # Check dataset info
            info = api.dataset_info(repo_id)
            print(f"\n  License: {getattr(info, 'license', 'NOT SPECIFIED')}")
            print(f"  Tags: {getattr(info, 'tags', [])}")

            print(f"\n  ✅ Use this repo: {repo_id}")
            break
        except Exception as e:
            print(f"  ❌ Not found or error: {e}")

    print("\n  ⚠️  NEXT STEPS:")
    print("  1. Load a few samples and inspect the annotation fields")
    print("  2. Record license in docs/datasets_licenses.md")
    print("  3. Run: !python scripts/convert_invoices.py")


def convert_invoices():
    """Main conversion logic for HF invoice dataset."""
    print("=" * 60)
    print("Converting HF Invoice dataset")
    print("=" * 60)

    try:
        from datasets import load_dataset
    except ImportError:
        print("  [ERROR] 'datasets' library not installed.")
        sys.exit(1)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    # Try candidate repos
    ds = None
    used_repo = None
    for repo_id in CANDIDATE_REPOS:
        try:
            print(f"  Trying to load: {repo_id}")
            ds = load_dataset(repo_id)
            used_repo = repo_id
            print(f"  ✅ Loaded: {repo_id}")
            break
        except Exception as e:
            print(f"  ❌ {repo_id}: {e}")

    if ds is None:
        print("  [ERROR] Could not load any invoice dataset.")
        print("  Verify the correct repo name and try again.")
        sys.exit(1)

    records = []
    review_records = []
    stats = Counter()

    # Inspect first sample to understand structure
    first_split = list(ds.keys())[0]
    first_sample = ds[first_split][0]
    print(f"\n  Sample keys: {list(first_sample.keys())}")
    print(f"  Splits available: {list(ds.keys())}")

    for split_name in ds.keys():
        split_data = ds[split_name]
        print(f"  Processing split '{split_name}': {len(split_data)} documents")

        for idx, sample in enumerate(split_data):
            source_key = str(sample.get("id", f"{idx:05d}"))
            doc_id = f"invoices_hf_{split_name}_{source_key}"

            ground_truth = {
                "invoice_number": "",
                "date": "",
                "supplier": "",
                "total": "",
            }
            annotations_raw = {}
            needs_review = False
            review_reasons = []

            # ── Try to extract ground truth ──
            # Donut-style datasets often have a "ground_truth" string
            # that is a JSON-encoded dict
            gt_raw = sample.get("ground_truth", sample.get("text", ""))
            if isinstance(gt_raw, str) and gt_raw.strip():
                try:
                    gt_parsed = json.loads(gt_raw)
                    if isinstance(gt_parsed, dict):
                        annotations_raw["parsed_ground_truth"] = gt_parsed
                        # Try to find our fields
                        for our_key, candidates in [
                            ("invoice_number", ["invoice_number", "invoice_no", "inv_no",
                                                  "invoice_id", "number", "no"]),
                            ("date", ["date", "invoice_date", "issue_date"]),
                            ("supplier", ["supplier", "vendor", "company", "seller",
                                          "vendor_name", "supplier_name"]),
                            ("total", ["total", "total_amount", "grand_total",
                                       "amount_due", "net_amount"]),
                        ]:
                            for cand in candidates:
                                val = gt_parsed.get(cand)
                                if val is not None and str(val).strip():
                                    ground_truth[our_key] = str(val).strip()
                                    break
                            # Also check nested "gt_parse" structure
                            gt_parse = gt_parsed.get("gt_parse", {})
                            if isinstance(gt_parse, dict) and not ground_truth[our_key]:
                                for cand in candidates:
                                    val = gt_parse.get(cand)
                                    if val is not None and str(val).strip():
                                        ground_truth[our_key] = str(val).strip()
                                        break
                except (json.JSONDecodeError, TypeError):
                    annotations_raw["raw_ground_truth"] = gt_raw

            # Direct field access (if not Donut-style)
            for our_key, candidates in [
                ("invoice_number", ["invoice_number", "invoice_no"]),
                ("date", ["date", "invoice_date"]),
                ("supplier", ["supplier", "vendor", "company"]),
                ("total", ["total", "total_amount"]),
            ]:
                if not ground_truth[our_key]:
                    for cand in candidates:
                        val = sample.get(cand)
                        if val is not None and str(val).strip():
                            ground_truth[our_key] = str(val).strip()
                            break

            # Detect language
            all_text = " ".join(v for v in ground_truth.values() if v)
            language = detect_lang(all_text)

            # Flag review
            non_empty = sum(1 for v in ground_truth.values() if v)
            if non_empty == 0:
                needs_review = True
                review_reasons.append("no_fields_extracted")

            annotations = {
                "origin_dataset": "invoices_hf",
                "hf_repo": used_repo,
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
                source="invoices_hf",
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

    # Write outputs
    output_path = Path("data/processed/invoices.jsonl")
    write_jsonl(records, output_path)

    if review_records:
        review_path = REVIEW_DIR / "invoices_review.jsonl"
        write_jsonl(review_records, review_path)

    # Summary
    print(f"\n  Invoice Dataset Conversion Summary:")
    print(f"  Repo used: {used_repo}")
    print(f"  Total records: {len(records)}")
    print(f"  Records needing review: {len(review_records)}")
    for key, count in sorted(stats.items()):
        print(f"    {key}: {count}")

    for field in ["invoice_number", "date", "supplier", "total"]:
        empty = sum(1 for r in records if not r["ground_truth"][field])
        print(f"  Empty '{field}': {empty}/{len(records)}")

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert HF Invoice dataset")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify the dataset (Phase A)")
    args = parser.parse_args()

    if args.verify_only:
        verify_invoices()
    else:
        convert_invoices()
